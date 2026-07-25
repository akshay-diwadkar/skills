#!/usr/bin/env python3
"""Bounded, phase-scoped repository task resolver."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
from knowledge.config import load_config, resolve_knowledge_directory
from knowledge.discovery import knowledge_output_prefix
from knowledge.indexing import shard_id
from knowledge.schemas import validate_schema_json
from refresh_knowledge import check_freshness

STOPWORDS = {
    "add",
    "change",
    "fix",
    "implement",
    "make",
    "update",
    "the",
    "and",
    "with",
    "for",
    "from",
    "into",
    "that",
    "this",
    "code",
    "file",
    "error",
    "issue",
}
CONFIG_NAMES = {"pyproject.toml", "package.json", "makefile", "gnumakefile", "tsconfig.json"}
CONFIG_EXTENSIONS = {".toml", ".yaml", ".yml", ".json", ".ini", ".cfg"}
CONFIG_PHRASES = {
    "ruff line length", "mypy strict", "pytest addopts", "package json script", "workflow trigger",
    "github actions matrix", "tool ruff", "tool pytest ini options", "eslint", "prettier", "tsconfig",
}
STRONG_CONFIG_TOKENS = {"ruff", "mypy", "eslint", "prettier", "tsconfig", "addopts", "ini_options", "workflow"}
TEST_PHRASES = {"failing assertion", "change the fixture", "update the regression test", "fix test", "assertion", "fixture", "rename test", "expected output"}
IMPLEMENTATION_WORDS = {"implement", "add", "fix", "support", "prevent", "handle", "refactor", "caller", "behavior"}
SecondaryRole = Literal["test", "configuration"]
PrimaryRole = Literal["source", "test", "configuration"]


@dataclass(frozen=True)
class TaskIntent:
    """Deterministic primary ownership and explicitly requested constraints."""

    primary_role: PrimaryRole
    secondary_roles: tuple[SecondaryRole, ...]
    reasons: tuple[str, ...]


def _split(value: str) -> set[str]:
    words = (
        re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
        .replace("_", " ")
        .replace("-", " ")
        .replace("/", " ")
        .replace(".", " ")
        .split()
    )
    return {word.lower() for word in words if len(word) > 1 and word.lower() not in STOPWORDS}


def _signals(task: str) -> dict[str, set[str]]:
    raw = re.findall(r"[A-Za-z_][A-Za-z0-9_./:-]*", task)
    return {
        "paths": {x.replace("\\", "/") for x in raw if "/" in x or re.search(r"\.[A-Za-z0-9]{1,5}$", x)},
        "symbols": {x for x in raw if re.search(r"[A-Z]|_", x) and "/" not in x},
        "terms": set().union(*(_split(x) for x in raw)) if raw else set(),
    }


def _role_order(roles: list[str]) -> list[PrimaryRole]:
    """Return deterministic roles with source owning mixed explicit work."""
    ordered: list[PrimaryRole] = []
    for role in ("source", "test", "configuration"):
        if role in roles:
            ordered.append(role)
    return ordered


def _explicit_path_roles(signals: dict[str, set[str]], files: list[dict[str, Any]], exact: bool) -> list[PrimaryRole]:
    matches: list[str] = []
    for path in signals["paths"]:
        for file in files:
            indexed = file["path"]
            if (indexed == path) if exact else (indexed.endswith("/" + path) or path.endswith("/" + indexed)):
                matches.append(file["role"])
    return _role_order(matches)


def _explicit_symbol_roles(signals: dict[str, set[str]], files: list[dict[str, Any]]) -> list[PrimaryRole]:
    return _role_order([file["role"] for file in files if set(file.get("symbols", [])) & signals["symbols"]])


def _is_test_creation_task(lowered: str) -> bool:
    return bool(re.search(r"\b(?:add|create|write)\b.{0,40}\b(?:regression )?tests?\b", lowered))


def _is_mixed_implementation_task(lowered: str, implementation: bool, test_evidence: bool, config_evidence: bool) -> bool:
    if not implementation or not (test_evidence or config_evidence):
        return False
    # "Add a regression test" owns a test; implementation support alongside it
    # makes test work a constraint instead.
    return not _is_test_creation_task(lowered) or "support" in lowered or "implement" in lowered


def classify_task_intent(task: str, signals: dict[str, set[str]], files: list[dict[str, Any]]) -> TaskIntent:
    """Classify ownership using indexed evidence before vocabulary."""
    explicit = signals["paths"]
    lowered = task.lower().replace("_", " ").replace("-", " ").replace(".", " ")
    for roles, reason in (
        (_explicit_path_roles(signals, files, True), "explicit indexed path matched"),
        (_explicit_path_roles(signals, files, False), "explicit indexed path suffix matched"),
        (_explicit_symbol_roles(signals, files), "explicit indexed symbol matched"),
    ):
        if roles:
            primary = roles[0]
            explicit_secondary = tuple(role for role in roles[1:] if role != "source")
            matched = next(
                (
                    file["path"]
                    for file in files
                    if file["role"] == primary
                    and (file["path"] in explicit or any(file["path"].endswith("/" + path) for path in explicit) or set(file.get("symbols", [])) & signals["symbols"])
                ),
                primary,
            )
            return TaskIntent(primary, explicit_secondary, (f"{reason} {matched}",))
    config_path = any(Path(path).suffix.lower() in CONFIG_EXTENSIONS or Path(path).name.lower() in CONFIG_NAMES for path in explicit)
    test_path = any("/test" in f"/{path.lower()}" or Path(path).name.lower().startswith("test_") for path in explicit)
    config_semantic = any(phrase in lowered for phrase in CONFIG_PHRASES)
    # pytest alone is deliberately not configuration evidence: it often names test code.
    pytest_config = "pytest" in lowered and any(key in lowered for key in ("addopts", "ini options", "configuration", "config"))
    test_semantic = any(phrase in lowered for phrase in TEST_PHRASES) or bool(re.search(r"\btest_[a-z0-9_]+\b|\btests?\b", lowered))
    config_evidence = config_path or config_semantic or pytest_config or "configuration" in lowered or bool(
        re.search(r"\b(?:addopts|line[- ]?length|permissions|matrix|package script|compiler|linter)\b", lowered)
    )
    test_evidence = test_path or test_semantic or ("fixture" in lowered and "pytest" in lowered)
    implementation = any(re.search(rf"\b{re.escape(word)}\b", lowered) for word in IMPLEMENTATION_WORDS)
    maintenance = bool(re.search(r"\b(assertion|fixture|rename|expected output|failing (?:\w+ )*test|correct (?:\w+ )*regression test)\b", lowered))
    reasons: list[str] = []
    if config_path:
        return TaskIntent("configuration", (), ("explicit configuration filename or extension",))
    if test_path:
        return TaskIntent("test", (), ("explicit test filename or test path",))
    if _is_mixed_implementation_task(lowered, implementation, test_evidence, config_evidence):
        reasons.append("strong implementation wording")
        mixed_secondary: list[SecondaryRole] = []
        if config_evidence:
            mixed_secondary.append("configuration")
        if test_evidence:
            mixed_secondary.append("test")
        reasons.extend(f"{role} work is a secondary constraint" for role in mixed_secondary)
        return TaskIntent("source", tuple(mixed_secondary), tuple(reasons))
    if _is_test_creation_task(lowered):
        return TaskIntent("test", (), ("task explicitly requests creation of a regression test",))
    if test_evidence and maintenance:
        return TaskIntent("test", (), ("strong test-maintenance wording",))
    if implementation:
        reasons.append("strong implementation wording")
    if config_evidence:
        reasons.append("strong configuration evidence")
    if test_evidence:
        reasons.append("strong test-maintenance evidence")
    if implementation:
        implementation_secondary: list[SecondaryRole] = []
        # Configuration precedes tests so mixed constraints have stable output.
        if config_evidence or "configuration" in lowered:
            implementation_secondary.append("configuration")
        if test_evidence:
            implementation_secondary.append("test")
        return TaskIntent("source", tuple(implementation_secondary), tuple(reasons))
    if config_evidence:
        return TaskIntent("configuration", (), tuple(reasons))
    return TaskIntent("source", (), ("ambiguous ownership defaults to source",))


def _load(root: Path, out: Path | str | None) -> tuple[Path, dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    directory = resolve_knowledge_directory(root, out, load_config(root))
    names = ["manifest.json", "repo-map.json", "symbols.json", "relationships.json"]
    if any(not (directory / x).is_file() for x in names):
        raise FileNotFoundError("Knowledge artifacts missing; run build first.")
    manifest, repo, catalog, relationships = [json.loads((directory / x).read_text()) for x in names]
    errors = sum(
        (
            validate_schema_json(manifest, "manifest.schema.json"),
            validate_schema_json(repo, "repo-map.schema.json"),
            validate_schema_json(catalog, "symbols.schema.json"),
            validate_schema_json(relationships, "relationships.schema.json"),
        ),
        [],
    )
    if errors:
        raise ValueError(f"Invalid knowledge artifacts: {errors}")
    return directory, manifest, repo, catalog, relationships


def _add(evidence: dict[str, tuple[float, str]], key: str, weight: float, family: str) -> None:
    if weight:
        evidence[key] = (weight, family)


def _lexical(
    files: list[dict[str, Any]], signals: dict[str, set[str]], weights: dict[str, float], freshness: str
) -> list[dict[str, Any]]:
    results = []
    for file in files:
        path = file["path"]
        evidence: dict[str, tuple[float, str]] = {}
        names = file.get("symbols", [])
        exact = [x for x in names if x in signals["symbols"]]
        if any(path == x or path.endswith("/" + x) for x in signals["paths"]):
            _add(evidence, f"exact_path: {path}", weights["exact_path"], "path")
        if exact:
            _add(evidence, f"exact_symbol: {exact[0]}", weights["exact_symbol"], "identifier")
        matched = signals["terms"] & _split(Path(path).stem)
        if matched:
            _add(evidence, f"filename: {sorted(matched)[0]}", weights["filename"], "path")
        symbol_terms = set().union(*(_split(x) for x in names)) if names else set()
        matched = signals["terms"] & symbol_terms
        if matched:
            _add(evidence, f"symbol_token: {sorted(matched)[0]}", weights["symbol_token"], "identifier")
        matched = signals["terms"] & _split(file["subsystem"])
        if matched:
            _add(evidence, f"subsystem: {sorted(matched)[0]}", weights["subsystem"], "subsystem")
        matched = signals["terms"] & _split(path)
        if matched:
            _add(evidence, f"text_match: {sorted(matched)[0]}", weights["text_match"], "path")
        if file["role"] == "configuration" and (file["path"] in signals["paths"] or signals["terms"] & STRONG_CONFIG_TOKENS):
            _add(evidence, f"configuration: {path}", weights["configuration"], "configuration")
        if file.get("generated"):
            _add(evidence, "generated_penalty", weights["generated_penalty"], "generated")
        if "vendor" in path.lower() or "node_modules" in path.lower():
            _add(evidence, "vendor_penalty", weights["vendor_penalty"], "ownership")
        if not file.get("language") and file["role"] == "source":
            _add(evidence, "unsupported_extractor_penalty", weights["unsupported_extractor_penalty"], "ownership")
        if freshness != "fresh":
            _add(evidence, "stale_knowledge_penalty", weights["stale_knowledge_penalty"], "freshness")
        score = sum(x[0] for x in evidence.values())
        if score > 0:
            results.append({"file": file, "score": score, "evidence": evidence})
    return sorted(results, key=lambda x: (-x["score"], x["file"]["path"]))


def _rerank(
    shortlist: list[dict[str, Any]], relationships: dict[str, Any], by_path: dict[str, Any], weights: dict[str, float]
) -> list[dict[str, Any]]:
    selected = {x["file"]["path"]: x for x in shortlist}
    seed = set(selected)
    # Include direct neighbours only; this is the sole controlled expansion.
    for edge in relationships.get("imports", []):
        if edge["source"] in seed or edge["target"] in seed:
            other = edge["target"] if edge["source"] in seed else edge["source"]
            if other in by_path and other not in selected:
                selected[other] = {"file": by_path[other], "score": 0.0, "evidence": {}}
    tests_by_target: dict[str, list[str]] = {}
    for edge in relationships.get("test_links", []):
        tests_by_target.setdefault(edge["target"], []).append(edge["source"])
    for path, item in selected.items():
        ev = item["evidence"]
        for test in sorted(tests_by_target.get(path, [])):
            _add(ev, f"tested_by: {test}", weights["related_test"], "test")
        for importer in sorted(relationships.get("reverse_imports", {}).get(path, [])):
            _add(ev, f"imported_by: {importer}", weights["reverse_import_relationship"], "import")
        for edge in relationships.get("imports", []):
            if edge["source"] == path:
                _add(ev, f"imports: {edge['target']}", weights["import_relationship"], "import")
        if Path(path).name.lower() in {"main.py", "app.py", "index.ts", "index.js", "server.js", "cli.py"}:
            _add(ev, f"entry_point: {path}", weights["entry_point"], "entry_point")
        item["score"] = sum(x[0] for x in ev.values())
    return sorted((x for x in selected.values() if x["score"] > 0), key=lambda x: (-x["score"], x["file"]["path"]))


def _symbols(directory: Path, catalog: dict[str, Any], paths: set[str]) -> dict[str, list[dict[str, Any]]]:
    answer: dict[str, list[dict[str, Any]]] = {x: [] for x in paths}
    wanted = {shard_id(x) for x in paths}
    for shard in catalog["shards"]:
        if shard["id"] in wanted:
            for symbol in json.loads((directory / shard["path"]).read_text())["symbols"]:
                if symbol["path"] in answer:
                    answer[symbol["path"]].append(symbol)
    return answer


def _configuration_key_candidates(task: str) -> list[str]:
    """Extract ordered key-shaped candidates without treating prose as keys."""
    quoted = re.findall(r"['\"]([^'\"]+)['\"]", task)
    dotted = re.findall(r"\b(?:[A-Za-z][\w-]*\.)+[A-Za-z][\w-]*\b", task)
    hyphenated = re.findall(r"\b[a-z][a-z0-9]*(?:[-_][a-z0-9]+)+\b", task.lower())
    phrases = [phrase for phrase in CONFIG_PHRASES if phrase in task.lower().replace("-", " ")]
    strong = sorted(term for term in _split(task) if len(term) > 3 and term not in STOPWORDS)
    return list(dict.fromkeys(quoted + dotted + hyphenated + phrases + strong))


def _configuration_match_score(line: str, candidate: str) -> int:
    """Rank active structural key matches above values, comments, and prose."""
    stripped = line.strip()
    if stripped.startswith(("#", ";", "//")):
        return -100
    normalized = candidate.lower().replace("-", "_")
    comparable = stripped.lower().replace("-", "_")
    escaped = re.escape(normalized)
    if re.match(rf'^\s*"?{escaped}"?\s*[=:]', comparable):
        return 90 if "." in normalized else 80
    if re.match(rf"^\s*{escaped}\s*=", comparable):
        return 85
    if re.match(rf'^\s*"{escaped}"\s*:', comparable):
        return 82
    key = normalized.rsplit(".", 1)[-1]
    if "." in normalized and re.match(rf"^\s*\[.*{re.escape(normalized.rsplit('.', 1)[0])}.*\]", comparable):
        return 45
    if re.match(rf'^\s*"?{re.escape(key)}"?\s*[=:]', comparable):
        return 70
    if re.search(rf"\b{escaped}\b", comparable):
        return 15
    return 0


def _structured_configuration_keys(path: str, lines: list[str]) -> dict[int, str]:
    """Track the small amount of structure needed to rank active config keys."""
    suffix = Path(path).suffix.lower()
    result: dict[int, str] = {}
    if Path(path).name.lower() in {"makefile", "gnumakefile"}:
        for index, line in enumerate(lines):
            match = re.match(r"^([A-Za-z0-9_.-]+)\s*:(?![=])", line)
            if match:
                result[index] = match.group(1)
        return result
    if suffix in {".toml", ".ini", ".cfg"}:
        section = ""
        for index, line in enumerate(lines):
            match = re.match(r"\s*\[([^]]+)\]", line)
            if match:
                section = match.group(1).strip()
            match = re.match(r"\s*([A-Za-z0-9_.-]+)\s*[=:]", line)
            if match and not line.lstrip().startswith(("#", ";")):
                result[index] = ".".join(part for part in (section, match.group(1)) if part)
        return result
    if suffix in {".yaml", ".yml"}:
        yaml_ancestors: list[tuple[int, str]] = []
        for index, line in enumerate(lines):
            match = re.match(r"^(\s*)([A-Za-z0-9_.-]+):", line)
            if not match or line.lstrip().startswith("#"):
                continue
            indent, key = len(match.group(1).expandtabs(2)), match.group(2)
            while yaml_ancestors and yaml_ancestors[-1][0] >= indent:
                yaml_ancestors.pop()
            result[index] = ".".join([name for _, name in yaml_ancestors] + [key])
            yaml_ancestors.append((indent, key))
        return result
    if suffix == ".json":
        json_ancestors: list[str] = []
        for index, line in enumerate(lines):
            match = re.match(r'\s*"([^"\\]+)"\s*:', line)
            if match:
                key = match.group(1)
                result[index] = ".".join(json_ancestors + [key])
                if "{" in line[line.find(":") + 1:]:
                    json_ancestors.append(key)
            closes = line.count("}")
            for _ in range(min(closes, len(json_ancestors))):
                json_ancestors.pop()
        return result
    return result


def _focused_text_range(root: Path, path: str, task: str, config: dict[str, Any]) -> tuple[int | None, int | None, str | None]:
    """Return the highest-ranked compact, active configuration-key range."""
    try:
        lines = (root / path).read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return None, None, None
    ranked = []
    structured = _structured_configuration_keys(path, lines)
    for candidate in _configuration_key_candidates(task):
        for index, line in enumerate(lines):
            score = _configuration_match_score(line, candidate)
            normalized = candidate.lower().replace("-", "_")
            structure = structured.get(index, "").lower().replace("-", "_")
            if structure == normalized:
                score = 120 if "." in normalized else 110
            elif Path(path).suffix.lower() == ".json" and "." in candidate:
                quoted_parts = [f'"{part}"' for part in candidate.split(".")]
                positions = [line.find(part) for part in quoted_parts]
                if all(position >= 0 for position in positions) and positions == sorted(positions):
                    score = 120
            elif structure.rsplit(".", 1)[-1:] == normalized.rsplit(".", 1)[-1:] and score >= 70:
                score = max(score, 100)
            if "." in candidate and score < 75:
                key = candidate.rsplit(".", 1)[-1].replace("-", "_")
                if re.match(rf"^\s*{re.escape(key)}\s*[=:]", line.strip().lower().replace("-", "_")):
                    section = candidate.rsplit(".", 1)[0].replace("-", "_")
                    if any(section in prior.strip().lower().replace("-", "_") for prior in lines[max(0, index - 8):index]):
                        score = 95
            ranked.append((score, index, candidate))
    score, index, needle = max(ranked, default=(0, 0, ""), key=lambda item: (item[0], -item[1], item[2]))
    if score >= 70:
        start = index
        for prior in range(index - 1, max(-1, index - 9), -1):
            previous = lines[prior].strip()
            if previous.startswith("[") or (previous.endswith(":") and not previous.startswith(("#", ";", "//"))):
                start = prior
                break
        limit = config["max_context_lines"]
        start = max(0, start - min(2, limit // 4))
        end = min(len(lines), index + 1 + min(4, limit - 1))
        if end - start > limit:
            end = start + limit
        return start + 1, end, needle
    return None, None, None


def _target(
    candidate: dict[str, Any], symbols: list[dict[str, Any]], signals: dict[str, set[str]], root: Path, task: str, config: dict[str, Any]
) -> dict[str, Any]:
    match = next((x for x in symbols if x["name"] in signals["symbols"]), None) or next(
        (x for x in symbols if _split(x["name"]) & signals["terms"]), None
    )
    file = candidate["file"]
    start_line = match["line_start"] if match else None
    end_line = match["line_end"] if match else None
    focused_key = None
    if not match and file["role"] == "configuration":
        start_line, end_line, focused_key = _focused_text_range(root, file["path"], task, config)
    evidence = [key for key, (weight, _) in sorted(candidate["evidence"].items()) if weight > 0]
    if focused_key:
        evidence.append(f"configuration_key: {focused_key}")
    return {
        "path": file["path"],
        "symbol": match["name"] if match else None,
        "start_line": start_line,
        "end_line": end_line,
        "role": file["role"],
        "evidence": sorted(set(evidence)),
        "question": f"Does {match['name'] if match else file['path']} own the requested behavior?",
    }


def _dedupe(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for item in items:
        old = output.get(item["path"])
        if not old:
            output[item["path"]] = item
        else:
            old["evidence"] = sorted(set(old["evidence"]) | set(item["evidence"]))
    return [output[path] for path in sorted(output)]


def evidence_for_test_target(test_path: str, source_path: str) -> str:
    """Evidence from the returned test target's perspective."""
    del test_path
    return f"tests: {source_path}"


def evidence_for_import_neighbor(primary_path: str, source_path: str, target_path: str) -> tuple[str, str]:
    """Return the target and its directional import evidence for one graph edge."""
    if source_path == primary_path:
        return target_path, f"dependency_of: {primary_path}"
    return source_path, f"imports: {primary_path}"


def _relationship_targets(
    primary_paths: set[str], relationships: dict[str, Any], by_path: dict[str, Any], root: Path, task: str,
    signals: dict[str, set[str]], config: dict[str, Any]
) -> list[dict[str, Any]]:
    """Return deterministic direct neighbours with evidence from the neighbour's perspective."""
    merged: dict[str, dict[str, Any]] = {}
    for edge in relationships.get("imports", []):
        source, target = edge["source"], edge["target"]
        if source in primary_paths and target not in primary_paths:
            adjacent, evidence = evidence_for_import_neighbor(source, source, target)
        elif target in primary_paths and source not in primary_paths:
            adjacent, evidence = evidence_for_import_neighbor(target, source, target)
        else:
            continue
        if adjacent not in by_path:
            continue
        item = merged.setdefault(adjacent, {"file": by_path[adjacent], "evidence": {}})
        _add(item["evidence"], evidence, config["weights"]["import_relationship"], "import")
    return _dedupe([_target(item, [], signals, root, task, config) for _, item in sorted(merged.items())])


def resolve_task(
    repo_root: Path | str, task: str, knowledge_dir: Path | str | None = None, phase: int | str = 1
) -> dict[str, Any]:
    if phase not in {1, 2, 3, "all"}:
        raise ValueError("phase must be 1, 2, 3, or all")
    root = Path(repo_root).resolve()
    directory, _, repo, catalog, relationships = _load(root, knowledge_dir)
    config = load_config(root)
    freshness = check_freshness(root, directory)["status"]
    signals = _signals(task)
    by_path = {x["path"]: x for x in repo["files"]}
    lexical = _lexical(repo["files"], signals, config["weights"], freshness)[:8]
    ranked = _rerank(lexical, relationships, by_path, config["weights"])
    lexical_paths = {item["file"]["path"] for item in lexical}
    intent = classify_task_intent(task, signals, repo["files"])
    primaries = [
        item for item in ranked
        if item["file"]["path"] in lexical_paths and item["file"]["role"] == intent.primary_role
    ][:3]
    if not primaries:
        primaries = [
            {
                "file": file,
                "score": 0.0,
                "evidence": {"role_fallback": (0.0, "ownership")},
            }
            for file in sorted(repo["files"], key=lambda item: item["path"])
            if file["role"] == intent.primary_role
        ][:3]
    symbol_map = _symbols(directory, catalog, {x["file"]["path"] for x in primaries})
    primary = [_target(x, symbol_map[x["file"]["path"]], signals, root, task, config) for x in primaries]
    primary_paths = {x["path"] for x in primary}
    tests = _dedupe(
        [
            _target(
                {
                    "file": by_path[x["source"]],
                    "evidence": {
                        evidence_for_test_target(x["source"], x["target"]): (config["weights"]["related_test"], "test")
                    },
                },
                [],
                signals, root, task, config,
            )
            for x in relationships.get("test_links", [])
            if x["target"] in primary_paths
        ]
    )
    impacts = _relationship_targets(primary_paths, relationships, by_path, root, task, signals, config)
    score = primaries[0]["score"] if primaries else 0
    margin = score - (primaries[1]["score"] if len(primaries) > 1 else 0)
    families = {family for weight, family in primaries[0]["evidence"].values() if weight > 0} if primaries else set()
    focused = bool(primary and primary[0]["start_line"])
    high = freshness == "fresh" and focused and margin >= config["confidence_margin"] and len(families) >= 2
    level = "high" if high else "medium" if primary else "low"
    terms = sorted(signals["terms"])
    output_prefix = knowledge_output_prefix(root, directory)
    strongest = sorted(signals["symbols"] or signals["terms"], key=lambda value: (-len(value), value))
    if primary and primary[0]["role"] == "configuration" and not focused:
        strongest = [rf"{re.escape(strongest[0])}\s*[:=]"] if strongest else []
    fallback = [] if high else [
        f"rg -n --glob {shlex.quote('!' + output_prefix + '/**')} -- {shlex.quote(term)}"
        for term in strongest[: (1 if level == "medium" else 3)]
    ]
    if not primary:
        reasons = ["no indexed owner matched the task terms"]
        uncertainties = ["run the targeted fallback search against authoritative source"]
    else:
        evidence_labels = primary[0]["evidence"]
        concrete = [label.replace("exact_symbol: ", "exact symbol matched ") for label in evidence_labels if label.startswith("exact_symbol:")]
        concrete += [label.replace("tested_by: ", "direct test relationship points to ") for label in evidence_labels if label.startswith("tested_by:")]
        reasons = concrete or [f"{primary[0]['role']} candidate matched task vocabulary"]
        uncertainties = []
        if primary[0]["role"] == "configuration" and not focused:
            uncertainties.append("no exact configuration key or focused range was located")
        if len(primaries) > 1 and margin < config["confidence_margin"]:
            uncertainties.append("candidate score separation is below the configured confidence margin")
        if len(families) < 2:
            uncertainties.append("no direct test, import, or entry-point evidence separates candidates")
        if high:
            reasons.append("top candidate exceeds the configured confidence margin")
    phases = {
        1: {
            "targets": primary,
            "question": "Which likely task owner owns the requested behavior or constraint?",
            "stop_condition": "Stop when ownership and the source contract are verified.",
            "expansion_triggers": ["ownership remains ambiguous", "source contradicts the index"],
        },
        2: {
            "targets": _dedupe(
                tests
                + [
                    _target(item, [], signals, root, task, config)
                    for item in ranked
                    if item["file"]["role"] in set(intent.secondary_roles)
                    and item["file"]["path"] not in primary_paths
                ]
            )[:3],
            "question": "Which direct tests, configuration, or represented constraints constrain the change?",
            "stop_condition": "Stop when direct constraints are understood.",
            "expansion_triggers": ["a compatibility constraint is unresolved"],
        },
        3: {
            "targets": impacts[:3],
            "question": "Which first-order callers or dependencies are affected?",
            "stop_condition": "Stop when affected contracts are explicit.",
            "expansion_triggers": ["cross-subsystem behavior is observed"],
        },
    }
    payload = {
        "task": task,
        "phase": phase,
        "knowledge_freshness": freshness,
        "task_terms": terms,
        "task_intent": {
            "primary_role": intent.primary_role,
            "secondary_roles": list(intent.secondary_roles),
            "reasons": list(intent.reasons),
        },
        "confidence": {"level": level, "score": round(score, 3), "reasons": reasons, "uncertainties": uncertainties},
        "fallback_searches": fallback,
    }
    payload.update(
        {"phases": [{"phase": key, **value} for key, value in phases.items()]}
        if phase == "all"
        else {"phase": int(phase), **phases[int(phase)]}
    )
    errors = validate_schema_json(payload, "resolver-result.schema.json")
    if errors:
        raise ValueError(f"Invalid resolver result: {errors}")
    return payload


def format_human(result: dict[str, Any]) -> str:
    targets = result.get("targets", []) if result.get("phase") != "all" else result["phases"][0]["targets"]
    return "\n".join(
        [
            f"# Task Resolution: {result['task']}",
            f"Confidence: {result['confidence']['level']}",
            *[f"- `{x['path']}:{x['start_line'] or '?'}-{x['end_line'] or '?'}` {x['symbol'] or ''}" for x in targets],
        ]
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("task")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output")
    parser.add_argument("--phase", choices=["1", "2", "3", "all"], default="1")
    parser.add_argument("--format", choices=["json", "human"], default="human")
    args = parser.parse_args()
    result = resolve_task(
        args.repo_root, args.task, args.output, args.phase if args.phase == "all" else int(args.phase)
    )
    print(json.dumps(result, indent=2) if args.format == "json" else format_human(result))
