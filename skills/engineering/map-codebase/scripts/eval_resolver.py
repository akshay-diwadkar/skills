#!/usr/bin/env python3
"""Run deterministic accuracy, retrieval-cost, and patch-outcome benchmarks."""

from __future__ import annotations

import ast
import json
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from build_knowledge import build_knowledge
from resolve_task import _split, resolve_task
from tokenizer import count_tokens

SKILL_DIR = SCRIPTS_DIR.parent
REPOSITORY_ROOT = SKILL_DIR.parents[2]
EVAL_DIR = REPOSITORY_ROOT / "tests" / "skills" / "map-codebase" / "eval"
CASES_PATH = EVAL_DIR / "cases.json"
QUALITY_CASES_PATH = EVAL_DIR / "quality-cases.json"
BASELINE_PATH = EVAL_DIR / "baseline.json"
BENCHMARK_PATH = SKILL_DIR / "references" / "benchmark.md"
ROLES = ("source", "test", "configuration")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def owner_matches(case: dict[str, Any], target: dict[str, Any] | None) -> bool:
    if target is None or target.get("path") != case["path"]:
        return False
    expected_symbol = case.get("symbol")
    return expected_symbol is None or target.get("symbol") == expected_symbol


def _measure(text: str) -> dict[str, int]:
    return {
        "tokens": count_tokens(text),
        "characters": len(text),
    }


def _target_text(root: Path, target: dict[str, Any]) -> str:
    content = (root / target["path"]).read_text(encoding="utf-8", errors="ignore")
    start, end = target.get("start_line"), target.get("end_line")
    if not start or not end:
        return content
    lines = content.splitlines(keepends=True)
    return "".join(lines[max(0, start - 1):min(len(lines), end)])


def resolver_context(root: Path, result: dict[str, Any]) -> tuple[dict[str, str], str]:
    """Return unique target ranges supplied to the resolver-scoped condition."""
    contexts: dict[str, str] = {}
    for target in result.get("targets", []):
        value = _target_text(root, target)
        previous = contexts.get(target["path"])
        if previous is None or len(value) > len(previous):
            contexts[target["path"]] = value
    rendered = "".join(f"\n### {path}\n{value}" for path, value in sorted(contexts.items()))
    return contexts, rendered


def grep_baseline_context(
    root: Path,
    repo_map: dict[str, Any],
    task: str,
) -> tuple[dict[str, str], str]:
    """Grep task keywords, then open every matching indexed file in full."""
    keywords = sorted(term for term in _split(task) if len(term) > 2)
    patterns = [re.compile(rf"\b{re.escape(term)}\b", flags=re.IGNORECASE) for term in keywords]
    contexts: dict[str, str] = {}
    hits: list[str] = []
    for item in repo_map["files"]:
        path = item["path"]
        try:
            content = (root / path).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        matching_lines = [
            f"{path}:{line_number}:{line}"
            for line_number, line in enumerate(content.splitlines(), start=1)
            if any(pattern.search(line) for pattern in patterns)
        ]
        if matching_lines:
            hits.extend(matching_lines)
            contexts[path] = content
    rendered = "\n".join(hits) + "".join(
        f"\n### {path}\n{value}" for path, value in sorted(contexts.items())
    )
    return contexts, rendered


def calculate_metrics(outcomes: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(outcomes)
    correct = sum(bool(item["correct"]) for item in outcomes)
    by_repository: dict[str, dict[str, int]] = defaultdict(lambda: {"correct": 0, "total": 0})
    for item in outcomes:
        values = by_repository[item["repo"]]
        values["total"] += 1
        values["correct"] += int(bool(item["correct"]))

    roles: dict[str, dict[str, float | int]] = {}
    for role in ROLES:
        true_positive = sum(bool(item["correct"]) and item["role"] == role for item in outcomes)
        false_positive = sum(item["predicted_role"] == role and not bool(item["correct"]) for item in outcomes)
        false_negative = sum(item["role"] == role and not bool(item["correct"]) for item in outcomes)
        predicted = true_positive + false_positive
        relevant = true_positive + false_negative
        roles[role] = {
            "true_positive": true_positive,
            "false_positive": false_positive,
            "false_negative": false_negative,
            "precision": true_positive / predicted if predicted else 0.0,
            "recall": true_positive / relevant if relevant else 0.0,
        }

    return {
        "total": total,
        "correct": correct,
        "hit_at_1": correct / total if total else 0.0,
        "repositories": {
            name: {
                **counts,
                "hit_at_1": counts["correct"] / counts["total"] if counts["total"] else 0.0,
            }
            for name, counts in sorted(by_repository.items())
        },
        "roles": roles,
    }


def calculate_retrieval_metrics(outcomes: list[dict[str, Any]]) -> dict[str, Any]:
    repositories: dict[str, Any] = {}
    for repository in sorted({item["repo"] for item in outcomes} | {"Overall"}):
        selected = outcomes if repository == "Overall" else [item for item in outcomes if item["repo"] == repository]
        groups = {}
        for label, correct in (("correct", True), ("incorrect", False)):
            group = [item for item in selected if bool(item["correct"]) is correct]
            resolver_tokens = sum(item["resolver_tokens"] for item in group)
            grep_tokens = sum(item["grep_tokens"] for item in group)
            resolver_characters = sum(item["resolver_characters"] for item in group)
            grep_characters = sum(item["grep_characters"] for item in group)
            groups[label] = {
                "cases": len(group),
                "resolver_tokens": resolver_tokens,
                "grep_tokens": grep_tokens,
                "resolver_characters": resolver_characters,
                "grep_characters": grep_characters,
                "token_savings": (
                    1 - resolver_tokens / grep_tokens
                    if correct and grep_tokens
                    else 0.0
                ),
                "character_savings": (
                    1 - resolver_characters / grep_characters
                    if correct and grep_characters
                    else 0.0
                ),
            }
        repositories[repository] = groups
    return repositories


def evaluate_cases(cases: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for case in cases:
        grouped[case["repo"]].append(case)

    outcomes: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="map-codebase-eval-") as temporary:
        temporary_root = Path(temporary)
        for repository, repository_cases in sorted(grouped.items()):
            fixture = EVAL_DIR / "repos" / repository
            working = temporary_root / repository
            shutil.copytree(fixture, working)
            knowledge = working / ".agent" / "knowledge"
            build_knowledge(working, knowledge)
            repo_map = load_json(knowledge / "repo-map.json")
            for case in repository_cases:
                result = resolve_task(working, case["task"], knowledge, phase=1)
                target = result["targets"][0] if result["targets"] else None
                _, resolver_text = resolver_context(working, result)
                _, grep_text = grep_baseline_context(working, repo_map, case["task"])
                resolver_cost = _measure(resolver_text)
                grep_cost = _measure(grep_text)
                outcomes.append(
                    {
                        **case,
                        "correct": owner_matches(case, target),
                        "confidence": result["confidence"]["level"],
                        "predicted_path": target.get("path") if target else None,
                        "predicted_symbol": target.get("symbol") if target else None,
                        "predicted_role": target.get("role") if target else None,
                        "resolver_tokens": resolver_cost["tokens"],
                        "resolver_characters": resolver_cost["characters"],
                        "grep_tokens": grep_cost["tokens"],
                        "grep_characters": grep_cost["characters"],
                    }
                )
    metrics = calculate_metrics(outcomes)
    metrics["retrieval"] = calculate_retrieval_metrics(outcomes)
    metrics["incorrect_high_confidence"] = sum(
        not item["correct"] and item["confidence"] == "high" for item in outcomes
    )
    return metrics, outcomes


def _replace_once(path: Path, before: str, after: str) -> bool:
    content = path.read_text(encoding="utf-8")
    if content.count(before) != 1:
        return False
    path.write_text(content.replace(before, after, 1), encoding="utf-8")
    return True


def _run_check(root: Path, command: list[str]) -> bool:
    resolved: list[str] = []
    for value in command:
        if value == "{python}":
            # Quality setup and repair can preserve both source size and filesystem
            # timestamp. Avoid a stale timestamp-based .pyc masking the repaired source.
            resolved.extend((sys.executable, "-B"))
        else:
            resolved.append(value)
    return subprocess.run(resolved, cwd=root, capture_output=True, timeout=30, check=False).returncode == 0


def _symbol_contains(path: Path, symbol: str | None, needle: str) -> bool:
    content = path.read_text(encoding="utf-8")
    if symbol is None:
        return needle in content
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return False
    lines = content.splitlines()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == symbol:
            segment = "\n".join(lines[node.lineno - 1:node.end_lineno])
            return needle in segment
    return False


def _simulate_quality_condition(
    prepared: Path,
    case: dict[str, Any],
    condition: str,
    destination: Path,
) -> dict[str, Any]:
    shutil.copytree(prepared, destination)
    target_path = destination / case["path"]
    knowledge = destination / ".agent" / "knowledge"
    repo_map = load_json(knowledge / "repo-map.json")
    if condition == "resolver":
        result = resolve_task(destination, case["task"], knowledge, phase=1)
        contexts, rendered = resolver_context(destination, result)
    else:
        contexts, rendered = grep_baseline_context(destination, repo_map, case["task"])

    matching_paths = [
        path for path, context in contexts.items()
        if case["repair_before"] in context
    ]
    applied_path = matching_paths[0] if len(matching_paths) == 1 else None
    applied = bool(
        applied_path
        and _replace_once(
            destination / applied_path,
            case["repair_before"],
            case["repair_after"],
        )
    )
    correct_owner = applied_path == case["path"]
    correct_symbol = bool(
        applied
        and correct_owner
        and _symbol_contains(target_path, case.get("symbol"), case["repair_after"])
    )
    tests_pass = applied and _run_check(destination, case["test"])
    cost = _measure(rendered)
    return {
        "condition": condition,
        "task": case["task"],
        "success": bool(correct_owner and correct_symbol and tests_pass),
        "applied_path": applied_path,
        "tokens": cost["tokens"],
        "characters": cost["characters"],
    }


def evaluate_quality(cases: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    outcomes: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="map-codebase-quality-") as temporary:
        root = Path(temporary)
        prepared_by_repo: dict[str, Path] = {}
        for repository in sorted({case["repo"] for case in cases}):
            prepared = root / f"prepared-{repository}"
            shutil.copytree(EVAL_DIR / "repos" / repository, prepared)
            for case in [item for item in cases if item["repo"] == repository]:
                if not _replace_once(
                    prepared / case["path"],
                    case["setup_before"],
                    case["setup_after"],
                ):
                    raise ValueError(f"Quality setup is not unique for {case['task']}")
                if _run_check(prepared, case["test"]):
                    raise ValueError(f"Quality setup did not make its test fail: {case['task']}")
            build_knowledge(prepared, prepared / ".agent" / "knowledge")
            prepared_by_repo[repository] = prepared
        for case_index, case in enumerate(cases):
            for condition in ("resolver", "grep"):
                outcomes.append(
                    _simulate_quality_condition(
                        prepared_by_repo[case["repo"]],
                        case,
                        condition,
                        root / f"{case_index}-{condition}",
                    )
                )
    metrics = {}
    for condition in ("resolver", "grep"):
        selected = [item for item in outcomes if item["condition"] == condition]
        successes = [item for item in selected if item["success"]]
        failures = [item for item in selected if not item["success"]]
        metrics[condition] = {
            "successes": len(successes),
            "total": len(selected),
            "success_rate": len(successes) / len(selected) if selected else 0.0,
            "tokens": sum(item["tokens"] for item in selected),
            "characters": sum(item["characters"] for item in selected),
            "median_tokens": (
                statistics.median(item["tokens"] for item in selected) if selected else 0
            ),
            "tokens_per_success": (
                sum(item["tokens"] for item in selected) / len(successes)
                if successes
                else 0.0
            ),
            "failed_tokens": sum(item["tokens"] for item in failures),
        }
    return metrics, outcomes


def render_benchmark(
    metrics: dict[str, Any],
    outcomes: list[dict[str, Any]],
    quality: dict[str, Any],
    quality_outcomes: list[dict[str, Any]],
) -> str:
    lines = [
        "# Resolver Benchmark",
        "",
        "Generated by `python scripts/eval_resolver.py` from committed fixtures. "
        "Token counts use `cl100k_base`; characters are exact Unicode code points.",
        "",
        "## Hit@1",
        "",
        "| Repository | Correct | Cases | Hit@1 |",
        "| --- | ---: | ---: | ---: |",
    ]
    for repository, values in metrics["repositories"].items():
        lines.append(f"| {repository} | {values['correct']} | {values['total']} | {values['hit_at_1']:.3f} |")
    lines.extend(
        [
            f"| **Overall** | **{metrics['correct']}** | **{metrics['total']}** | **{metrics['hit_at_1']:.3f}** |",
            "",
            "## Precision and Recall by Role",
            "",
            "| Role | True positive | False positive | False negative | Precision | Recall |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for role in ROLES:
        values = metrics["roles"][role]
        lines.append(
            f"| {role} | {values['true_positive']} | {values['false_positive']} | "
            f"{values['false_negative']} | {values['precision']:.3f} | {values['recall']:.3f} |"
        )

    lines.extend(
        [
            "",
            "## Retrieval Cost",
            "",
            "Resolver cost counts returned source ranges; an unfocused target counts as a full-file read. "
            "The baseline counts grep output plus every matching indexed file opened in full. "
            "Incorrect resolutions receive zero credited savings.",
            "",
            "| Repository | Outcome | Cases | Resolver tokens | Grep tokens | Token savings | Resolver chars | Grep chars | Char savings |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for repository, groups in metrics["retrieval"].items():
        for label in ("correct", "incorrect"):
            values = groups[label]
            lines.append(
                f"| {repository} | {label} | {values['cases']} | {values['resolver_tokens']} | "
                f"{values['grep_tokens']} | {values['token_savings']:.1%} | "
                f"{values['resolver_characters']} | {values['grep_characters']} | "
                f"{values['character_savings']:.1%} |"
            )

    lines.extend(
        [
            "",
            "## Confidence Safety",
            "",
            f"Incorrect high-confidence targets: **{metrics['incorrect_high_confidence']}**.",
            "",
            "## Deterministic Patch-Outcome Evaluation",
            "",
            "This is a deterministic patch simulator, not a live LLM benchmark. It proves that supplied "
            "context contains enough information to make the expected scoped edit and pass existing tests; "
            "it does not measure model generalization.",
            "",
            "| Condition | Success | Rate | Tokens | Median tokens | Tokens/success | Characters | Failed-attempt tokens |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for condition in ("resolver", "grep"):
        values = quality[condition]
        lines.append(
            f"| {condition} | {values['successes']}/{values['total']} | {values['success_rate']:.1%} | "
            f"{values['tokens']} | {values['median_tokens']:.0f} | "
            f"{values['tokens_per_success']:.1f} | "
            f"{values['characters']} | {values['failed_tokens']} |"
        )
    failed_quality = [item for item in quality_outcomes if not item["success"]]
    lines.extend(["", "Quality failures: " + ("none." if not failed_quality else "")])
    for item in failed_quality:
        lines.append(f"- {item['condition']}: {item['task']} (applied: {item['applied_path'] or 'none'})")

    correct_cost = metrics["retrieval"]["Overall"]["correct"]
    lines.extend(
        [
            "",
            "## Before/After Evidence",
            "",
            "| Measure | Before | After |",
            "| --- | ---: | ---: |",
            f"| Hit@1 | 0.667 | {metrics['hit_at_1']:.3f} |",
            f"| Configuration recall | 0.278 | {metrics['roles']['configuration']['recall']:.3f} |",
            "| JavaScript Hit@1 | 0.733 | "
            f"{metrics['repositories']['javascript-small']['hit_at_1']:.3f} |",
            "| Correct-resolution context tokens | Not measured | "
            f"{correct_cost['resolver_tokens']} resolver vs. "
            f"{correct_cost['grep_tokens']} grep "
            f"({correct_cost['token_savings']:.1%} savings) |",
            "| Patch success | Not measured | "
            f"{quality['resolver']['successes']}/{quality['resolver']['total']} resolver vs. "
            f"{quality['grep']['successes']}/{quality['grep']['total']} grep |",
        ]
    )

    failures = [item for item in outcomes if not item["correct"]]
    lines.extend(["", "## Misses", ""])
    if not failures:
        lines.append("None.")
    else:
        lines.extend(["| Repository | Task | Expected | Predicted | Confidence |", "| --- | --- | --- | --- | --- |"])
        for item in failures:
            expected = item["path"] + (f"::{item['symbol']}" if item.get("symbol") else "")
            predicted = item["predicted_path"] or "(no target)"
            if item.get("predicted_symbol"):
                predicted += f"::{item['predicted_symbol']}"
            lines.append(
                f"| {item['repo']} | {item['task']} | {expected} | {predicted} | {item['confidence']} |"
            )
    return "\n".join(lines) + "\n"


def baseline_failures(
    metrics: dict[str, Any],
    baseline: dict[str, Any],
    outcomes: list[dict[str, Any]] | None = None,
    quality: dict[str, Any] | None = None,
) -> list[str]:
    failures = []
    if metrics["hit_at_1"] < baseline["overall"]:
        failures.append(
            f"overall hit@1 {metrics['hit_at_1']:.3f} is below committed baseline {baseline['overall']:.3f}"
        )
    for repository, floor in sorted(baseline["repositories"].items()):
        actual = metrics["repositories"][repository]["hit_at_1"]
        if actual < floor:
            failures.append(f"{repository} hit@1 {actual:.3f} is below committed baseline {floor:.3f}")
    javascript_hit = metrics["repositories"]["javascript-small"]["hit_at_1"]
    if javascript_hit < 0.85:
        failures.append(f"javascript-small hit@1 {javascript_hit:.3f} is below required 0.850")
    if outcomes is None or quality is None:
        return failures
    legacy = [item for item in outcomes if item["repo"] != "realistic-large"]
    legacy_hit = sum(item["correct"] for item in legacy) / len(legacy)
    if legacy_hit < 0.667:
        failures.append(f"legacy hit@1 {legacy_hit:.3f} is below 0.667")
    if metrics["roles"]["source"]["precision"] < 0.902:
        failures.append("source precision regressed below 0.902")
    if metrics["roles"]["test"]["precision"] < 0.720:
        failures.append("test precision regressed below 0.720")
    if metrics["roles"]["configuration"]["recall"] <= 0.278:
        failures.append("configuration recall did not improve above 0.278")
    if metrics["incorrect_high_confidence"]:
        failures.append(f"{metrics['incorrect_high_confidence']} incorrect resolution(s) were high confidence")
    correct = metrics["retrieval"]["Overall"]["correct"]
    if correct["token_savings"] < 0.5 or correct["character_savings"] < 0.5:
        failures.append("aggregate correct-resolution savings are below 50%")
    for repository, groups in metrics["retrieval"].items():
        if repository != "Overall" and groups["correct"]["cases"]:
            if groups["correct"]["resolver_tokens"] >= groups["correct"]["grep_tokens"]:
                failures.append(f"{repository} resolver tokens are not below grep tokens")
            if groups["correct"]["resolver_characters"] >= groups["correct"]["grep_characters"]:
                failures.append(f"{repository} resolver characters are not below grep characters")
    if quality["resolver"]["success_rate"] < quality["grep"]["success_rate"]:
        failures.append("resolver patch success is below grep patch success")
    if quality["resolver"]["tokens"] >= quality["grep"]["tokens"]:
        failures.append("resolver patch tokens are not below grep patch tokens")
    return failures


def main() -> int:
    cases = load_json(CASES_PATH)
    quality_cases = load_json(QUALITY_CASES_PATH)
    baseline = load_json(BASELINE_PATH)
    counts = Counter(case["repo"] for case in cases)
    if set(counts.values()) != {30}:
        print(f"Error: expected exactly 30 cases per repository, found {dict(sorted(counts.items()))}", file=sys.stderr)
        return 1
    metrics, outcomes = evaluate_cases(cases)
    quality, quality_outcomes = evaluate_quality(quality_cases)
    BENCHMARK_PATH.write_text(
        render_benchmark(metrics, outcomes, quality, quality_outcomes),
        encoding="utf-8",
    )
    failures = baseline_failures(metrics, baseline, outcomes, quality)
    print(f"Resolver benchmark: {metrics['correct']}/{metrics['total']} hit@1={metrics['hit_at_1']:.3f}")
    print(
        "Patch benchmark: "
        f"resolver={quality['resolver']['successes']}/{quality['resolver']['total']} "
        f"grep={quality['grep']['successes']}/{quality['grep']['total']}"
    )
    for failure in failures:
        print(f"Error: {failure}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
