#!/usr/bin/env python3
"""Selective, phase-scoped repository task resolver."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path: sys.path.insert(0, str(SCRIPTS_DIR))
from knowledge.config import load_config
from knowledge.schemas import validate_schema_json
from refresh_knowledge import check_freshness

STOPWORDS = {"add", "change", "fix", "implement", "make", "update", "the", "and", "with", "for", "from", "into", "that", "this", "code", "file", "error", "issue"}


def _shard_id(path: str) -> str: return (path.split("/", 1)[0] if "/" in path else "root").replace(".", "_")


def _split(value: str) -> list[str]:
    words = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value).replace("_", " ").replace("-", " ").replace("/", " ").replace(".", " ").split()
    result: set[str] = set()
    for word in words:
        lower = word.lower()
        if len(lower) > 1 and lower not in STOPWORDS:
            result.add(lower)
            if lower.endswith("s") and len(lower) > 3: result.add(lower[:-1])
    return sorted(result)


def _signals(task: str) -> dict[str, set[str]]:
    quoted = re.findall(r"[\"'`]([^\"'`]+)[\"'`]", task)
    raw = re.findall(r"[A-Za-z_][A-Za-z0-9_./:-]*", task)
    exact_paths = {item.replace("\\", "/") for item in raw if "/" in item or re.search(r"\.[A-Za-z0-9]{1,5}$", item)}
    exact_symbols = {item for item in raw if re.search(r"[A-Z]|_", item) and "/" not in item}
    vocabulary = set()
    for item in raw + quoted: vocabulary.update(_split(item))
    return {"paths": exact_paths, "symbols": exact_symbols, "terms": vocabulary}


def _load_base(root: Path, output: Path | None) -> tuple[Path, dict[str, Any], dict[str, Any], dict[str, Any]]:
    directory = output or root / load_config(root)["output_dir"]
    names = ["manifest.json", "repo-map.json", "symbols.json", "relationships.json"]
    if any(not (directory / name).is_file() for name in names): raise FileNotFoundError("Knowledge artifacts missing; run build first.")
    manifest, repo, catalog, relationships = [json.loads((directory / name).read_text(encoding="utf-8")) for name in names]
    errors = sum((validate_schema_json(manifest, "manifest.schema.json"), validate_schema_json(repo, "repo-map.schema.json"), validate_schema_json(catalog, "symbols.schema.json"), validate_schema_json(relationships, "relationships.schema.json")), [])
    if errors: raise ValueError(f"Invalid knowledge artifacts: {errors}")
    return directory, manifest, repo, relationships | {"_catalog": catalog}


def _score(files: list[dict[str, Any]], relationships: dict[str, Any], signals: dict[str, set[str]], config: dict[str, Any], freshness: str) -> list[dict[str, Any]]:
    weights = config["weights"]; imports = {(edge["source"], edge["target"]) for edge in relationships.get("imports", [])}; reverse = relationships.get("reverse_imports", {})
    candidates: list[dict[str, Any]] = []
    for file in files:
        path, stem = file["path"], Path(file["path"]).stem
        evidence: dict[str, float] = {}
        if any(path == value or path.endswith("/" + value) for value in signals["paths"]): evidence[f"exact_path: {path}"] = weights["exact_path"]
        file_terms = set(_split(path))
        filename_terms = set(_split(stem))
        symbol_terms = set().union(*(_split(name) for name in file.get("symbols", []))) if file.get("symbols") else set()
        exact = [name for name in file.get("symbols", []) if name in signals["symbols"]]
        if exact: evidence[f"exact_symbol: {exact[0]}"] = weights["exact_symbol"]
        if signals["terms"] & filename_terms: evidence[f"filename_match: {sorted(signals['terms'] & filename_terms)[0]}"] = weights["filename"]
        if signals["terms"] & symbol_terms: evidence[f"symbol_token: {sorted(signals['terms'] & symbol_terms)[0]}"] = weights["symbol_token"]
        if signals["terms"] & file_terms: evidence[f"text_match: {sorted(signals['terms'] & file_terms)[0]}"] = weights["text_match"]
        if file.get("generated"): evidence["generated_file_penalty"] = weights["generated_penalty"]
        if "vendor" in path.lower() or "node_modules" in path.lower(): evidence["vendor_file_penalty"] = weights["vendor_penalty"]
        if not file.get("language") and file["role"] == "source": evidence["unsupported_extractor_penalty"] = weights["unsupported_extractor_penalty"]
        if freshness != "fresh": evidence["stale_knowledge_penalty"] = weights["stale_knowledge_penalty"]
        score = sum(evidence.values())
        if score > 0: candidates.append({"file": file, "score": score, "evidence": evidence, "exact": bool(exact), "relationship_count": sum(1 for edge in imports if path in edge) + len(reverse.get(path, []))})
    return sorted(candidates, key=lambda item: (-item["score"], item["file"]["path"]))


def _load_symbols(directory: Path, catalog: dict[str, Any], paths: set[str]) -> dict[str, list[dict[str, Any]]]:
    selected = {_shard_id(path) for path in paths}; symbols: dict[str, list[dict[str, Any]]] = {path: [] for path in paths}
    for shard in catalog.get("shards", []):
        if shard["id"] not in selected: continue
        for symbol in json.loads((directory / shard["path"]).read_text(encoding="utf-8"))["symbols"]:
            if symbol["path"] in symbols: symbols[symbol["path"]].append(symbol)
    return symbols


def _target(root: Path, candidate: dict[str, Any], symbols: list[dict[str, Any]], signals: dict[str, set[str]]) -> dict[str, Any]:
    file = candidate["file"]; match = next((item for item in symbols if item["name"] in signals["symbols"]), None)
    if match is None:
        terms = signals["terms"]
        match = next((item for item in symbols if terms & set(_split(item["name"]))), None)
    start = end = None
    if match: start, end = match["line_start"], match["line_end"]
    else:
        try:
            lines = (root / file["path"]).read_text(encoding="utf-8", errors="ignore").splitlines()
            matches = [index + 1 for index, line in enumerate(lines) if any(term in line.lower() for term in signals["terms"])]
            if matches: start, end = max(1, matches[0] - 3), min(len(lines), matches[0] + 6)
        except OSError: pass
    return {"path": file["path"], "symbol": match["name"] if match else None, "start_line": start, "end_line": end, "role": file["role"], "evidence": [key for key, value in sorted(candidate["evidence"].items()) if value], "question": f"Does {match['name'] if match else file['path']} own the requested behavior?"}


def resolve_task(repo_root: Path | str, task: str, knowledge_dir: Path | str | None = None, phase: int | str = 1) -> dict[str, Any]:
    if phase not in {1, 2, 3, "all"}: raise ValueError("phase must be 1, 2, 3, or all")
    root = Path(repo_root).resolve(); config = load_config(root)
    directory, manifest, repo, relationship_data = _load_base(root, Path(knowledge_dir).resolve() if knowledge_dir else None)
    catalog = relationship_data.pop("_catalog"); freshness = check_freshness(root, directory)["status"]; signals = _signals(task)
    ranked = _score(repo["files"], relationship_data, signals, config, freshness)
    primary_candidates = [item for item in ranked if item["file"]["role"] == "source"][:3]
    selected_paths = {item["file"]["path"] for item in primary_candidates}; symbol_map = _load_symbols(directory, catalog, selected_paths)
    primary = [_target(root, item, symbol_map[item["file"]["path"]], signals) for item in primary_candidates]
    primary_paths = {item["path"] for item in primary}
    by_path = {item["path"]: item for item in repo["files"]}
    tests = [_target(root, {"file": by_path[edge["source"]], "evidence": {f"direct_test: {edge['source']}": config["weights"]["related_test"]}}, [], signals) for edge in relationship_data.get("test_links", []) if edge["target"] in primary_paths and edge["source"] in by_path][:3]
    configs = [_target(root, item, [], signals) for item in ranked if item["file"]["role"] == "configuration"][:2]
    impacts = [_target(root, {"file": by_path[edge["target"] if edge["source"] in primary_paths else edge["source"]], "evidence": {"import_relationship": config["weights"]["import_relationship"]}}, [], signals) for edge in relationship_data.get("imports", []) if (edge["source"] in primary_paths) ^ (edge["target"] in primary_paths)][:3]
    score = primary_candidates[0]["score"] if primary_candidates else 0; margin = score - (primary_candidates[1]["score"] if len(primary_candidates) > 1 else 0)
    categories = len({key.split(":", 1)[0] for item in primary_candidates[:1] for key, value in item["evidence"].items() if value > 0})
    high = bool(primary and primary[0]["symbol"] and categories >= 2 and margin >= config["weights"]["text_match"] and freshness == "fresh")
    level = "high" if high else "medium" if primary and freshness == "fresh" else "low"
    fallback = [] if level != "low" else [f"rg -n --glob '!{directory.name}/**' '{term}'" for term in sorted(signals["terms"])[:3]]
    phases = {1: {"targets": primary, "question": "Which implementation owns the requested behavior?", "stop_condition": "Stop when ownership and the source contract are verified.", "expansion_triggers": ["ownership remains ambiguous", "source contradicts the index"]}, 2: {"targets": tests + configs, "question": "Which tests, interfaces, or configuration constrain the change?", "stop_condition": "Stop when direct constraints are understood.", "expansion_triggers": ["a compatibility constraint is unresolved"]}, 3: {"targets": impacts, "question": "Which first-order callers or dependencies are affected?", "stop_condition": "Stop when affected contracts are explicit.", "expansion_triggers": ["cross-subsystem behavior is observed"]}}
    payload: dict[str, Any] = {"task": task, "phase": phase, "knowledge_freshness": freshness, "task_terms": sorted(signals["terms"]), "confidence": {"level": level, "score": round(score, 3), "reasons": ["fresh knowledge and diverse exact evidence" if high else "ownership still requires source verification"], "uncertainties": [] if high else ["Do not trust ownership until authoritative source is read."]}, "fallback_searches": fallback}
    if phase == "all": payload["phases"] = [{"phase": number, **value} for number, value in phases.items()]
    else: payload.update({"phase": int(phase), **phases[int(phase)]})
    errors = validate_schema_json(payload, "resolver-result.schema.json")
    if errors: raise ValueError(f"Invalid resolver result: {errors}")
    return payload


def format_human(result: dict[str, Any]) -> str:
    targets = result.get("targets", []) if result.get("phase") != "all" else result["phases"][0]["targets"]
    return "\n".join([f"# Task Resolution: {result['task']}", f"Confidence: {result['confidence']['level']}", *[f"- `{item['path']}:{item['start_line'] or '?'}-{item['end_line'] or '?'}` {item['symbol'] or ''}" for item in targets]])


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("task"); parser.add_argument("--repo-root", default="."); parser.add_argument("--output"); parser.add_argument("--phase", choices=["1", "2", "3", "all"], default="1"); parser.add_argument("--format", choices=["json", "human"], default="human")
    args = parser.parse_args(); result = resolve_task(args.repo_root, args.task, args.output, args.phase if args.phase == "all" else int(args.phase)); print(json.dumps(result, indent=2) if args.format == "json" else format_human(result)); return 0

if __name__ == "__main__": raise SystemExit(main())
