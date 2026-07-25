#!/usr/bin/env python3
"""Bounded, phase-scoped repository task resolver."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
from knowledge.config import load_config
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
CONFIG_TERMS = {"config", "configuration", "setting", "settings", "ruff", "mypy", "pytest", "line", "length", "toml", "yaml", "yml", "ini"}
TEST_TERMS = {"test", "tests", "testing", "failing", "failure", "assert", "fixture", "regression"}


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


def _task_roles(task: str, signals: dict[str, set[str]], files: list[dict[str, Any]]) -> set[str]:
    explicit = signals["paths"]
    matched_roles = {
        file["role"]
        for file in files
        if any(file["path"] == path or file["path"].endswith("/" + path) for path in explicit)
    }
    terms = signals["terms"]
    if terms & CONFIG_TERMS or any(Path(path).suffix in {".toml", ".yaml", ".yml", ".ini"} for path in explicit):
        matched_roles.add("configuration")
    if terms & TEST_TERMS or any("test" in path.lower() for path in explicit):
        matched_roles.add("test")
    if {"configuration", "test"} <= matched_roles:
        matched_roles.add("source")
    return matched_roles or {"source"}


def _load(root: Path, out: Path | None) -> tuple[Path, dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    directory = out or root / load_config(root)["output_dir"]
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
        if file["role"] == "configuration" and (signals["terms"] & CONFIG_TERMS or file["path"] in signals["paths"]):
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


def _target(candidate: dict[str, Any], symbols: list[dict[str, Any]], signals: dict[str, set[str]]) -> dict[str, Any]:
    match = next((x for x in symbols if x["name"] in signals["symbols"]), None) or next(
        (x for x in symbols if _split(x["name"]) & signals["terms"]), None
    )
    file = candidate["file"]
    return {
        "path": file["path"],
        "symbol": match["name"] if match else None,
        "start_line": match["line_start"] if match else None,
        "end_line": match["line_end"] if match else None,
        "role": file["role"],
        "evidence": [key for key, (weight, _) in sorted(candidate["evidence"].items()) if weight],
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
    return list(output.values())


def resolve_task(
    repo_root: Path | str, task: str, knowledge_dir: Path | str | None = None, phase: int | str = 1
) -> dict[str, Any]:
    if phase not in {1, 2, 3, "all"}:
        raise ValueError("phase must be 1, 2, 3, or all")
    root = Path(repo_root).resolve()
    directory, _, repo, catalog, relationships = _load(root, Path(knowledge_dir).resolve() if knowledge_dir else None)
    config = load_config(root)
    freshness = check_freshness(root, directory)["status"]
    signals = _signals(task)
    by_path = {x["path"]: x for x in repo["files"]}
    lexical = _lexical(repo["files"], signals, config["weights"], freshness)[:8]
    ranked = _rerank(lexical, relationships, by_path, config["weights"])
    requested_roles = _task_roles(task, signals, repo["files"])
    role_order = ["source", "configuration", "test"] if requested_roles == {"source", "configuration", "test"} else [role for role in ("source", "configuration", "test") if role in requested_roles]
    primaries = [item for role in role_order for item in ranked if item["file"]["role"] == role][:3]
    symbol_map = _symbols(directory, catalog, {x["file"]["path"] for x in primaries})
    primary = [_target(x, symbol_map[x["file"]["path"]], signals) for x in primaries]
    primary_paths = {x["path"] for x in primary}
    tests = _dedupe(
        [
            _target(
                {
                    "file": by_path[x["source"]],
                    "evidence": {f"tested_by: {x['source']}": (config["weights"]["related_test"], "test")},
                },
                [],
                signals,
            )
            for x in relationships.get("test_links", [])
            if x["target"] in primary_paths
        ]
    )
    impacts = _dedupe(
        [
            _target(
                {
                    "file": by_path[x["target"] if x["source"] in primary_paths else x["source"]],
                    "evidence": {f"imports: {x['target'] if x['source'] in primary_paths else x['source']}": (config["weights"]["import_relationship"], "import")},
                },
                [],
                signals,
            )
            for x in relationships.get("imports", [])
            if (x["source"] in primary_paths) ^ (x["target"] in primary_paths)
        ]
    )
    score = primaries[0]["score"] if primaries else 0
    margin = score - (primaries[1]["score"] if len(primaries) > 1 else 0)
    families = {family for weight, family in primaries[0]["evidence"].values() if weight > 0} if primaries else set()
    focused = bool(primary and primary[0]["start_line"])
    high = freshness == "fresh" and focused and margin >= config["confidence_margin"] and len(families) >= 2
    level = "high" if high else "medium" if primary else "low"
    terms = sorted(signals["terms"])
    fallback = (
        []
        if high
        else [
            f"rg -n --glob '!{directory.name}/**' -- {shlex.quote(term)}"
            for term in terms[: (1 if level == "medium" else 3)]
        ]
    )
    reasons = (
        [f"{len(families)} independent evidence families support the primary target"]
        if high
        else (
            [
                "primary target lacks a focused indexed range"
                if not focused
                else "primary candidates have limited independent evidence"
            ]
            if primary
            else ["no indexed implementation matched the task terms"]
        )
    )
    uncertainties = (
        []
        if high
        else (
            ["verify ownership in source before expanding"]
            if primary
            else ["use the targeted fallback search to locate an owner"]
        )
    )
    phases = {
        1: {
            "targets": primary,
            "question": "Which likely task owner owns the requested behavior or constraint?",
            "stop_condition": "Stop when ownership and the source contract are verified.",
            "expansion_triggers": ["ownership remains ambiguous", "source contradicts the index"],
        },
        2: {
            "targets": _dedupe(tests + [_target(item, [], signals) for item in ranked if item["file"]["role"] == "configuration" and item["file"]["path"] not in primary_paths])[:3],
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
