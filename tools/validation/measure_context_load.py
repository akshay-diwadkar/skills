#!/usr/bin/env python3
"""Measure and enforce deterministic instruction and runtime context load."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Any, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "benchmarks" / "context-load-budgets.json"
REPORT_PATH = ROOT / "benchmarks" / "reports" / "context-load.json"
INVOCATION_POLICY_PATH = ROOT / "invocation-policy.json"
MANDATORY_RULES_PATH = ROOT / "tests" / "repository" / "mandatory_skill_rules.json"
TOKENIZER_PATH = (
    ROOT / "skills" / "engineering" / "map-codebase" / "scripts" / "tokenizer" / "__init__.py"
)
REPORT_REPOSITORY_PATH = "benchmarks/reports/context-load.json"
LINK_RE = re.compile(r"!?\[[^\]]*\]\((?:<([^>]+)>|([^\)\s]+))")
ABSOLUTE_PATH_RE = re.compile(r"(?:^|[\s\"'])(?:[A-Za-z]:/|/[A-Za-z0-9_.-]+/)")
METRICS = (
    "top_level",
    "pre_action",
    "phase_references",
    "worst_references",
    "tool_output",
    "repair_diagnostic",
)


def _tokenizer() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "context_load_tokenizer",
        TOKENIZER_PATH,
        submodule_search_locations=[str(TOKENIZER_PATH.parent)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load tokenizer: {TOKENIZER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(_read_utf8(path).encode("utf-8"))


def _read_utf8(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{path}: reference content must be UTF-8 text") from exc


def _tokens(text: str, tokenizer: ModuleType) -> int:
    return int(tokenizer.count_tokens(text))


def skill_paths(root: Path = ROOT) -> list[Path]:
    return sorted((root / "skills").glob("*/*/SKILL.md"))


def _within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def _normalize_value(value: Any, substitutions: list[tuple[str, str]]) -> Any:
    if isinstance(value, str):
        normalized = value.replace("\\", "/")
        for actual, placeholder in substitutions:
            normalized = normalized.replace(actual.replace("\\", "/"), placeholder)
        if ABSOLUTE_PATH_RE.search(normalized):
            raise ValueError(f"runtime output retained an absolute path: {normalized}")
        return normalized
    if isinstance(value, list):
        return [_normalize_value(item, substitutions) for item in value]
    if isinstance(value, dict):
        return {key: _normalize_value(item, substitutions) for key, item in value.items()}
    return value


def _runtime_substitutions(root: Path, skill: Path, temp: Path, run_dir: Path) -> list[tuple[str, str]]:
    values = [
        (str(run_dir.resolve()), "{run_dir}"),
        (str(skill.resolve()), "{skill_dir}"),
        (str(root.resolve()), "{repo_root}"),
        (str(temp.resolve()), "{temp_dir}"),
        (sys.executable, "{python}"),
        (str(Path(sys.executable).resolve()), "{python}"),
    ]
    return sorted(values, key=lambda item: len(item[0]), reverse=True)


def _expand_input(value: str, temp: Path) -> str:
    replacements = {
        "{fixture_file}": str(temp / "fixture.json"),
        "{fixture_dir}": str(temp),
        "{future_file}": str(temp / "future-output.json"),
    }
    result = value
    for placeholder, path in replacements.items():
        result = result.replace(placeholder, path)
    return result


def _command_inputs(spec: Mapping[str, Any], temp: Path, *, omit: str | None = None) -> list[str]:
    result: list[str] = []
    for name, value in spec["representative_inputs"].items():
        if name == omit:
            continue
        result.extend(["--input", f"{name}={_expand_input(str(value), temp)}"])
    return result


def _run_runtime_case(
    root: Path,
    skill: Path,
    manifest: Mapping[str, Any],
    spec: Mapping[str, Any],
    temp: Path,
    *,
    diagnostic: bool,
) -> tuple[dict[str, Any], str]:
    run_dir = temp / f"{skill.name}-run"
    argv = [sys.executable, str(skill / "scripts" / "cli.py"), "--repo-root", str(root.resolve())]
    stateless = manifest.get("mode", "stateful") == "stateless"
    if not stateless:
        argv.extend(["--run-dir", str(run_dir)])
    omitted = str(spec["diagnostic_input"]) if diagnostic else None
    argv.extend(_command_inputs(spec, temp, omit=omitted))
    argv.extend(["--format", "json", "run" if diagnostic and stateless else "start" if diagnostic else "doctor"])
    result = subprocess.run(
        argv,
        cwd=root,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if not result.stdout.strip():
        raise ValueError(f"{skill.name}: runtime case emitted no JSON: {result.stderr.strip()}")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{skill.name}: runtime case emitted invalid JSON") from exc
    if diagnostic:
        codes = [item.get("code") for item in payload.get("diagnostics", [])]
        if result.returncode == 0 or payload.get("status") != "error" or codes != ["input.required"]:
            raise ValueError(f"{skill.name}: diagnostic case must emit exactly input.required")
    elif result.returncode != 0 or payload.get("status") != "ready":
        raise ValueError(f"{skill.name}: doctor case failed: {result.stderr.strip() or result.stdout.strip()}")
    normalized = _normalize_value(payload, _runtime_substitutions(root, skill, temp, run_dir))
    return payload, _canonical_json(normalized)


def _markdown_targets(path: Path, skill: Path) -> set[Path]:
    if path.suffix.casefold() != ".md":
        return set()
    targets: set[Path] = set()
    for match in LINK_RE.finditer(_read_utf8(path)):
        raw = match.group(1) or match.group(2)
        if raw.startswith(("#", "http://", "https://", "mailto:")):
            continue
        target = (path.parent / raw.split("#", 1)[0]).resolve()
        if not _within(target, skill):
            raise ValueError(f"{path}: linked context escapes skill package: {raw}")
        if target.is_file():
            targets.add(target)
    return targets


def _reachable(paths: Iterable[Path], skill: Path) -> set[Path]:
    found = {path.resolve() for path in paths}
    pending = list(found)
    while pending:
        source = pending.pop()
        for target in _markdown_targets(source, skill):
            if target not in found:
                found.add(target)
                pending.append(target)
    return found


def _path_measure(paths: Iterable[Path], skill: Path, tokenizer: ModuleType) -> dict[str, Any]:
    resolved = sorted({path.resolve() for path in paths})
    return {
        "tokens": sum(_tokens(_read_utf8(path), tokenizer) for path in resolved),
        "paths": [path.relative_to(skill.resolve()).as_posix() for path in resolved],
    }


def _static_read(raw: str, skill: Path) -> Path | None:
    prefix = "{skill_dir}/"
    if not raw.startswith(prefix):
        return None
    path = (skill / raw[len(prefix) :]).resolve()
    if not _within(path, skill) or not path.is_file():
        raise ValueError(f"{skill.name}: invalid static required read: {raw}")
    return path


def _phase_measurements(skill: Path, manifest: Mapping[str, Any], tokenizer: ModuleType) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for phase, phase_spec in manifest.get("phases", {}).items():
        required_roots = {
            path
            for raw in phase_spec.get("required_reads", [])
            for path in [_static_read(str(raw), skill)]
            if path is not None
        }
        required = _reachable(required_roots, skill)
        conditional_rows: list[dict[str, Any]] = []
        conditional_union: set[Path] = set()
        for conditional in phase_spec.get("conditional_reads", []):
            roots = {
                path
                for raw in conditional.get("paths", [])
                for path in [_static_read(str(raw), skill)]
                if path is not None
            }
            reached = _reachable(roots, skill)
            conditional_union.update(reached)
            row = _path_measure(reached, skill, tokenizer)
            row["condition"] = {
                "input": conditional["input"],
                "values": list(conditional["values"]),
            }
            conditional_rows.append(row)
        required_row = _path_measure(required, skill, tokenizer)
        worst_row = _path_measure(required | conditional_union, skill, tokenizer)
        result[phase] = {
            "required": required_row,
            "conditional": conditional_rows,
            "worst": worst_row,
        }
    return result


def _doctor_required_paths(payload: Mapping[str, Any], skill: Path) -> set[Path]:
    paths: set[Path] = set()
    for item in payload.get("required_reads", []):
        if not isinstance(item, Mapping) or not isinstance(item.get("path"), str):
            raise ValueError(f"{skill.name}: doctor required_reads must contain paths")
        path = Path(str(item["path"])).resolve()
        if not _within(path, skill) or not path.is_file():
            raise ValueError(f"{skill.name}: doctor required read escapes or is missing: {path}")
        paths.add(path)
    if (skill / "SKILL.md").resolve() not in paths:
        raise ValueError(f"{skill.name}: doctor must require SKILL.md before action")
    return paths


def _source_hash(skill: Path, reference_paths: Iterable[Path]) -> str:
    paths = {
        skill / "SKILL.md",
        skill / "skill-protocol.json",
        skill / "scripts" / "cli.py",
        skill / "scripts" / "_skill_protocol_runtime.py",
        skill / "scripts" / "_diagnostic_contract.py",
        *reference_paths,
    }
    digest = hashlib.sha256()
    resolved_paths = [path.resolve() for path in paths if path.is_file()]
    for path in sorted(resolved_paths, key=lambda item: item.relative_to(skill.resolve()).as_posix()):
        digest.update(path.relative_to(skill.resolve()).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(_read_utf8(path).encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def _validate_config(config: Mapping[str, Any], root: Path) -> list[str]:
    errors: list[str] = []
    names = {path.parent.name for path in skill_paths(root)}
    configured = set(config.get("skills", {}))
    policy = set(_json(root / "invocation-policy.json").get("skills", {}))
    rules = _json(root / "tests" / "repository" / "mandatory_skill_rules.json")
    protected = {str(rule.get("id")): str(rule.get("skill")) for rule in rules}
    covered = {str(rule.get("skill")) for rule in rules}
    if names != configured or names != policy or names != covered:
        errors.append("skill inventory must match discovery, invocation policy, budgets, and mandatory rules")
    categories = set(config.get("category_budgets", {}))
    required_categories = {"router", "model_helper", "user_orchestrator"}
    if categories != required_categories:
        errors.append("category_budgets must define router, model_helper, and user_orchestrator")
    if config.get("baseline", {}).get("status") not in {"draft", "established"}:
        errors.append("baseline status must be draft or established")
    for name, spec in config.get("skills", {}).items():
        skill = next((path.parent for path in skill_paths(root) if path.parent.name == name), None)
        if skill is None:
            continue
        manifest = _json(skill / "skill-protocol.json")
        required = {item["name"] for item in manifest["inputs"] if item["required"]}
        supplied = set(spec.get("representative_inputs", {}))
        if supplied != required:
            errors.append(f"{name}: representative inputs must match required manifest inputs")
        if spec.get("diagnostic_input") not in required:
            errors.append(f"{name}: diagnostic_input must name a required input")
        if spec.get("category") not in categories:
            errors.append(f"{name}: unknown context-load category")
        by_name = {item["name"]: item for item in manifest["inputs"]}
        for input_name, value in spec.get("representative_inputs", {}).items():
            choices = by_name[input_name].get("choices", [])
            if choices and value not in choices:
                errors.append(f"{name}: representative {input_name} is not a declared choice")
    seen: set[str] = set()
    for exception in config.get("exceptions", []):
        exception_id = str(exception.get("id", ""))
        if not exception_id or exception_id in seen:
            errors.append("context-load exception IDs must be non-empty and unique")
        seen.add(exception_id)
        skill_name = str(exception.get("skill", ""))
        if skill_name not in names or exception.get("metric") not in METRICS:
            errors.append(f"{exception_id}: exception has unknown skill or metric")
        if exception.get("direction") not in {"increase", "decrease"}:
            errors.append(f"{exception_id}: exception direction must be increase or decrease")
        if exception.get("scope") not in {None, "delta"}:
            errors.append(f"{exception_id}: exception scope must be delta when supplied")
        if not str(exception.get("rationale", "")).strip():
            errors.append(f"{exception_id}: exception requires a rationale")
        try:
            expires = dt.date.fromisoformat(str(exception.get("expires", "")))
        except ValueError:
            errors.append(f"{exception_id}: exception requires an ISO expiry date")
        else:
            if expires < dt.date.today():
                errors.append(f"{exception_id}: context-load exception expired on {expires.isoformat()}")
        if exception.get("metric") == "phase_references" and not exception.get("phase"):
            errors.append(f"{exception_id}: phase reference exception requires a phase")
        skill = next((path.parent for path in skill_paths(root) if path.parent.name == skill_name), None)
        for relative in exception.get("supporting_paths", []):
            if skill is None or not (skill / str(relative)).is_file():
                errors.append(f"{exception_id}: missing supporting path {relative}")
        for rule_id in exception.get("protected_rule_ids", []):
            if protected.get(str(rule_id)) != skill_name:
                errors.append(f"{exception_id}: protected rule {rule_id} does not belong to {skill_name}")
    return errors


def build_report(root: Path = ROOT, config_path: Path | None = None) -> dict[str, Any]:
    config_file = config_path or root / "benchmarks" / "context-load-budgets.json"
    config = _json(config_file)
    config_errors = _validate_config(config, root)
    if config_errors:
        raise ValueError("; ".join(config_errors))
    tokenizer = _tokenizer()
    rows: dict[str, Any] = {}
    with tempfile.TemporaryDirectory(prefix="context-load-") as temp_name:
        temp = Path(temp_name).resolve()
        (temp / "fixture.json").write_text("{}\n", encoding="utf-8")
        for skill_md in skill_paths(root):
            skill = skill_md.parent.resolve()
            name = skill.name
            manifest = _json(skill / "skill-protocol.json")
            spec = config["skills"][name]
            doctor_payload, doctor_output = _run_runtime_case(
                root, skill, manifest, spec, temp, diagnostic=False
            )
            _, diagnostic_output = _run_runtime_case(root, skill, manifest, spec, temp, diagnostic=True)
            phases = _phase_measurements(skill, manifest, tokenizer)
            reference_paths = set((skill / "references").rglob("*")) if (skill / "references").is_dir() else set()
            reference_files = {path.resolve() for path in reference_paths if path.is_file()}
            worst_references = _path_measure(reference_files, skill, tokenizer)
            pre_action_paths = _doctor_required_paths(doctor_payload, skill)
            top_level = _tokens(_read_utf8(skill_md), tokenizer)
            tool_output = _tokens(doctor_output, tokenizer)
            repair_diagnostic = _tokens(diagnostic_output, tokenizer)
            pre_action = _path_measure(pre_action_paths, skill, tokenizer)["tokens"] + tool_output
            phase_max = max((row["worst"]["tokens"] for row in phases.values()), default=0)
            worst_context = top_level + worst_references["tokens"] + max(tool_output, repair_diagnostic)
            rows[name] = {
                "path": skill_md.relative_to(root).as_posix(),
                "category": spec["category"],
                "source_hash": _source_hash(skill, reference_files),
                "metrics": {
                    "top_level": top_level,
                    "pre_action": pre_action,
                    "phase_references": phase_max,
                    "worst_references": worst_references["tokens"],
                    "tool_output": tool_output,
                    "repair_diagnostic": repair_diagnostic,
                    "worst_context": worst_context,
                },
                "pre_action_paths": [path.relative_to(skill).as_posix() for path in sorted(pre_action_paths)],
                "worst_reference_paths": worst_references["paths"],
                "phases": phases,
            }
    aggregate_metrics = {
        metric: sum(int(row["metrics"][metric]) for row in rows.values())
        for metric in (*METRICS, "worst_context")
    }
    return {
        "schema_version": 2,
        "tokenizer": "cl100k_base (vendored, SHA-256 verified)",
        "config_sha256": _sha256_file(config_file),
        "baseline": config["baseline"],
        "aggregate_metrics": aggregate_metrics,
        "skills": rows,
    }


def _default_limit(config: Mapping[str, Any], row: Mapping[str, Any], metric: str) -> int:
    if metric in {"top_level", "pre_action", "worst_references"}:
        return int(config["category_budgets"][row["category"]][metric])
    return int(config["shared_budgets"][metric])


def _matching_exception(
    config: Mapping[str, Any],
    skill: str,
    metric: str,
    phase: str | None,
    direction: str,
    *,
    scope: str,
) -> Mapping[str, Any] | None:
    for exception in config.get("exceptions", []):
        if (
            exception.get("skill") == skill
            and exception.get("metric") == metric
            and exception.get("direction") == direction
            and exception.get("phase") == phase
            and exception.get("scope") in {None, scope}
        ):
            return exception
    return None


def budget_errors(report: Mapping[str, Any], config: Mapping[str, Any]) -> list[str]:
    if config.get("baseline", {}).get("status") != "established":
        return []
    errors: list[str] = []
    used: set[str] = set()
    for name, row in report["skills"].items():
        for metric in ("top_level", "pre_action", "worst_references", "tool_output", "repair_diagnostic"):
            value = int(row["metrics"][metric])
            default = _default_limit(config, row, metric)
            exception = _matching_exception(
                config, name, metric, None, "increase", scope="absolute"
            )
            limit = int(exception["max_tokens"]) if exception is not None else default
            if value > default and exception is not None:
                used.add(str(exception["id"]))
            if value > limit:
                errors.append(f"{name}: {metric} {value} exceeds budget {limit}")
        phase_default = int(config["shared_budgets"]["phase_references"])
        for phase, phase_row in row["phases"].items():
            value = int(phase_row["worst"]["tokens"])
            exception = _matching_exception(
                config, name, "phase_references", phase, "increase", scope="absolute"
            )
            limit = int(exception["max_tokens"]) if exception is not None else phase_default
            if value > phase_default and exception is not None:
                used.add(str(exception["id"]))
            if value > limit:
                errors.append(f"{name}:{phase}: phase_references {value} exceeds budget {limit}")
    configured = {
        str(item["id"])
        for item in config.get("exceptions", [])
        if item.get("direction") == "increase" and item.get("scope") != "delta"
    }
    for exception_id in sorted(configured - used):
        errors.append(f"{exception_id}: context-load exception is stale or unnecessary")
    return errors


def _git_report(ref: str, root: Path) -> dict[str, Any] | None:
    result = subprocess.run(
        ["git", "show", f"{ref}:{REPORT_REPOSITORY_PATH}"],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode:
        return None
    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    return report if report.get("schema_version") == 2 else None


def _metric_values(row: Mapping[str, Any]) -> dict[tuple[str, str | None], int]:
    values: dict[tuple[str, str | None], int] = {
        (metric, None): int(row["metrics"][metric]) for metric in METRICS if metric != "phase_references"
    }
    values.update(
        {("phase_references", phase): int(value["worst"]["tokens"]) for phase, value in row["phases"].items()}
    )
    return values


def delta_errors(
    report: Mapping[str, Any], base: Mapping[str, Any] | None, config: Mapping[str, Any]
) -> list[str]:
    if base is None or config.get("baseline", {}).get("status") != "established":
        return []
    errors: list[str] = []
    reduction_percent = float(config["large_reduction_percent"])
    for name in sorted(set(report["skills"]) & set(base.get("skills", {}))):
        current_values = _metric_values(report["skills"][name])
        base_values = _metric_values(base["skills"][name])
        for key in sorted(set(current_values) & set(base_values)):
            metric, phase = key
            current = current_values[key]
            previous = base_values[key]
            delta = current - previous
            allowance = int(config["delta_budgets"][metric])
            if delta > allowance:
                exception = _matching_exception(
                    config, name, metric, phase, "increase", scope="delta"
                )
                if exception is None or current > int(exception["max_tokens"]):
                    suffix = f":{phase}" if phase else ""
                    errors.append(f"{name}{suffix}: {metric} increased by {delta}, budget {allowance}")
            reduction_allowance = max(allowance, int(previous * reduction_percent / 100))
            if -delta > reduction_allowance:
                exception = _matching_exception(
                    config, name, metric, phase, "decrease", scope="delta"
                )
                if exception is None:
                    suffix = f":{phase}" if phase else ""
                    errors.append(
                        f"{name}{suffix}: {metric} decreased by {-delta}; document a content-reduction exception"
                    )
    return errors


def validate_report(
    path: Path = REPORT_PATH,
    root: Path = ROOT,
    config_path: Path | None = None,
    compare_ref: str | None = None,
) -> list[str]:
    label = path.relative_to(root) if path.is_relative_to(root) else path
    if not path.is_file():
        return [f"Missing {label}"]
    try:
        committed = _json(path)
        current = build_report(root, config_path)
        config = _json(config_path or root / "benchmarks" / "context-load-budgets.json")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [f"{label}: cannot measure context load: {exc}"]
    errors: list[str] = []
    if committed != current:
        errors.append(f"{label}: generated report is stale; run measure_context_load.py --write")
        errors.extend(_report_differences(committed, current))
    errors.extend(budget_errors(current, config))
    if compare_ref:
        errors.extend(delta_errors(current, _git_report(compare_ref, root), config))
    return errors


def _report_differences(expected: Any, actual: Any, path: str = "report", limit: int = 20) -> list[str]:
    differences: list[str] = []

    def visit(left: Any, right: Any, current_path: str) -> None:
        if len(differences) >= limit:
            return
        if type(left) is not type(right):
            differences.append(
                f"{current_path}: committed type {type(left).__name__}, measured type {type(right).__name__}"
            )
            return
        if isinstance(left, dict):
            for key in sorted(set(left) | set(right)):
                if key not in left:
                    differences.append(f"{current_path}.{key}: missing from committed report")
                elif key not in right:
                    differences.append(f"{current_path}.{key}: missing from measured report")
                else:
                    visit(left[key], right[key], f"{current_path}.{key}")
                if len(differences) >= limit:
                    return
            return
        if isinstance(left, list):
            if len(left) != len(right):
                differences.append(f"{current_path}: committed length {len(left)}, measured length {len(right)}")
                return
            for index, (left_item, right_item) in enumerate(zip(left, right, strict=True)):
                visit(left_item, right_item, f"{current_path}[{index}]")
                if len(differences) >= limit:
                    return
            return
        if left != right:
            differences.append(f"{current_path}: committed {left!r}, measured {right!r}")

    visit(expected, actual, path)
    if len(differences) == limit:
        differences.append("report: additional differences omitted")
    return differences


def markdown_summary(report: Mapping[str, Any], base: Mapping[str, Any] | None = None) -> str:
    lines = [
        "## Context-load budgets",
        "",
        "| Skill | Top | Pre-action | Phase max | References | Tool | Diagnostic | Worst context | Δ worst |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, row in sorted(report["skills"].items()):
        metrics = row["metrics"]
        delta = "—"
        if base is not None and name in base.get("skills", {}):
            delta = f"{int(metrics['worst_context']) - int(base['skills'][name]['metrics']['worst_context']):+d}"
        lines.append(
            f"| {name} | {metrics['top_level']} | {metrics['pre_action']} | "
            f"{metrics['phase_references']} | {metrics['worst_references']} | {metrics['tool_output']} | "
            f"{metrics['repair_diagnostic']} | {metrics['worst_context']} | {delta} |"
        )
    totals = report["aggregate_metrics"]
    lines.extend(
        [
            "",
            f"Aggregate worst-context tokens: **{totals['worst_context']}**. "
            "Counts use the vendored, integrity-checked offline tokenizer.",
            "",
        ]
    )
    return "\n".join(lines)


def _write_report(report: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--write", action="store_true", help="Regenerate the committed report")
    action.add_argument("--check", action="store_true", help="Validate and enforce the committed report")
    parser.add_argument("--compare-ref", help="Trusted Git ref containing a compatible base report")
    parser.add_argument("--summary-file", type=Path, help="Write a Markdown totals and changes table")
    args = parser.parse_args()
    try:
        report = build_report()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Context-load measurement failed: {exc}", file=sys.stderr)
        return 1
    base = _git_report(args.compare_ref, ROOT) if args.compare_ref else None
    if args.write:
        _write_report(report, REPORT_PATH)
    else:
        errors = validate_report(compare_ref=args.compare_ref)
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
    if args.summary_file:
        args.summary_file.parent.mkdir(parents=True, exist_ok=True)
        with args.summary_file.open("a", encoding="utf-8") as handle:
            handle.write(markdown_summary(report, base))
    print("Context-load report written." if args.write else "Context-load report is current and within budget.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
