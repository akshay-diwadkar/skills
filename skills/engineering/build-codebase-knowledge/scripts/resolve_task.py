#!/usr/bin/env python3
"""Bounded, evidence-backed task resolver for codebase knowledge v2."""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path
from typing import Any
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path: sys.path.insert(0, str(SCRIPTS_DIR))
from knowledge.config import load_config
from knowledge.schemas import validate_schema_json
from refresh_knowledge import check_freshness

def _load(root: Path, output: Path | None) -> tuple[Path, dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    directory = output or root / load_config(root)["output_dir"]
    required = ["manifest.json", "repo-map.json", "symbols.json", "relationships.json"]
    if any(not (directory / name).is_file() for name in required): raise FileNotFoundError("Knowledge v2 artifacts missing; run build first.")
    manifest, repo, catalog, relationships = [json.loads((directory / name).read_text(encoding="utf-8")) for name in required]
    errors = validate_schema_json(manifest, "manifest.schema.json") + validate_schema_json(repo, "repo-map.schema.json") + validate_schema_json(catalog, "symbols.schema.json") + validate_schema_json(relationships, "relationships.schema.json")
    if errors: raise ValueError(f"Invalid knowledge artifacts: {errors}")
    symbols: list[dict[str, Any]] = []
    for shard in catalog["shards"]: symbols.extend(json.loads((directory / shard["path"]).read_text(encoding="utf-8"))["symbols"])
    return directory, manifest, repo, relationships, symbols

def _terms(task: str) -> list[str]:
    return sorted({x.lower() for x in re.findall(r"[A-Za-z_][A-Za-z0-9_./-]*", task) if len(x) > 2})
def _intent(task: str) -> list[str]:
    lower = task.lower(); pairs = {"bug": ["fix", "bug", "error"], "feature": ["add", "implement", "create"], "test": ["test", "assert"], "configuration": ["config", "toml", "yaml", "setting"], "security": ["security", "auth", "password", "token"], "performance": ["performance", "optimize", "slow"], "refactor": ["refactor", "restructure"]}
    return [name for name, words in pairs.items() if any(word in lower for word in words)] or ["feature"]
def _target(file: dict[str, Any], symbol: dict[str, Any] | None, score: float, breakdown: dict[str, float], freshness: str) -> dict[str, Any]:
    evidence = [f"{key}={value}" for key, value in sorted(breakdown.items()) if value]
    return {"path": file["path"], "symbol": symbol["name"] if symbol else None, "start_line": symbol["line_start"] if symbol else 1, "end_line": symbol["line_end"] if symbol else min(max(file["line_count"], 1), 120), "role": file["role"], "score": round(min(score, 1.0), 3), "score_breakdown": breakdown, "evidence": evidence, "reasons": evidence, "question_to_answer": "Verify this source contract before editing.", "read_reason": "Highest task-vocabulary and repository-relationship match.", "freshness": freshness}
def resolve_task(repo_root: Path | str, task: str, knowledge_dir: Path | str | None = None) -> dict[str, Any]:
    root = Path(repo_root).resolve(); directory, manifest, repo, relationships, symbols = _load(root, Path(knowledge_dir).resolve() if knowledge_dir else None); freshness = check_freshness(root, directory)["status"]
    terms = _terms(task); intents = _intent(task); files = repo["files"]; by_path = {f["path"]: f for f in files}; symbols_by_path: dict[str, list[dict[str, Any]]] = {}
    for symbol in symbols: symbols_by_path.setdefault(symbol["path"], []).append(symbol)
    ranked: list[tuple[float, dict[str, Any], dict[str, Any] | None, dict[str, float]]] = []
    for file in files:
        path_lower = file["path"].lower(); breakdown = {"exact_path": 1.0 if any(t in path_lower and "/" in t for t in terms) else 0.0, "filename": min(0.35, 0.12 * sum(t in Path(path_lower).stem for t in terms)), "vocabulary": min(0.25, 0.05 * sum(t in path_lower for t in terms)), "role": 0.1 if ("test" in intents and file["role"] == "test") or ("configuration" in intents and file["role"] == "configuration") else 0.0}
        matched = next((s for s in symbols_by_path.get(file["path"], []) if s["name"].lower() in terms), None)
        breakdown["exact_symbol"] = 0.7 if matched else 0.0
        breakdown["symbol_vocabulary"] = min(0.35, 0.12 * sum(term in symbol["name"].lower() for symbol in symbols_by_path.get(file["path"], []) for term in terms))
        score = sum(breakdown.values())
        if score: ranked.append((score, file, matched, breakdown))
    ranked.sort(key=lambda item: (-item[0], item[1]["path"]))
    primaries = [_target(f, s, score, b, freshness) for score, f, s, b in ranked if f["role"] == "source"][:3]
    primary_paths = {p["path"] for p in primaries}; tests = []
    for link in relationships["test_links"]:
        if link["target"] in primary_paths: tests.append(_target(by_path[link["source"]], None, 0.75, {"test_link": 0.75}, freshness))
    if not tests: tests = [_target(f, s, score, b, freshness) for score, f, s, b in ranked if f["role"] == "test"][:3]
    configs = [_target(f, s, score, b, freshness) for score, f, s, b in ranked if f["role"] == "configuration"][:2]
    dependencies = []
    for edge in relationships["imports"]:
        if edge["source"] in primary_paths or edge["target"] in primary_paths:
            other = edge["target"] if edge["source"] in primary_paths else edge["source"]
            if other not in primary_paths: dependencies.append(_target(by_path[other], None, 0.55, {"first_order_dependency": 0.55}, freshness))
    dependencies = dependencies[:3]
    score = ranked[0][0] if ranked else 0.0; margin = score - (ranked[1][0] if len(ranked) > 1 else 0.0); level = "high" if score >= .7 and margin >= .1 and freshness == "fresh" else "medium" if score >= .1 and freshness == "fresh" else "low"
    uncertainties = ([] if level == "high" else ["Verify ownership and runtime behavior in source before editing."]) + ([] if freshness == "fresh" else [f"Knowledge is {freshness}; refresh or verify changed paths."])
    selected = primaries + tests + configs + dependencies; lines = sum(t["end_line"] - t["start_line"] + 1 for t in selected)
    result = {"task": task, "knowledge_freshness": freshness, "intent": intents, "task_terms": terms, "confidence": {"level": level, "score": round(min(score, 1.0), 3), "reasons": ["Exact repository signals and role links were scored deterministically."], "uncertainties": uncertainties}, "primary_targets": primaries, "related_tests": tests[:3], "related_configuration": configs[:2], "interfaces_and_dependencies": dependencies, "read_phases": [{"phase": 1, "targets": primaries, "why": "Establish implementation ownership.", "question": "Which contract changes?", "stop_when": "A target symbol and direct behavior are verified.", "expand_when": "Ownership or behavior remains ambiguous."}, {"phase": 2, "targets": tests[:3] + configs[:2], "why": "Verify assertions and external constraints.", "question": "What must remain compatible?", "stop_when": "Direct assertions/config are understood.", "expand_when": "Tests conflict or configuration is re-exported."}, {"phase": 3, "targets": dependencies, "why": "Read only essential first-order contracts.", "question": "Which interfaces are affected?", "stop_when": "Interfaces are explicit.", "expand_when": "Cross-subsystem behavior is observed."}], "fallback_searches": ([] if level == "high" else [f"rg -n --glob '!{directory.name}/**' '{term}'" for term in terms[:3]]), "skip_targets": repo.get("generated_paths", [])[:5] + ["vendor/", "node_modules/", "dist/"], "source_validation_required": True, "estimated_exploration_cost": {"files_recommended": len(selected), "unique_files": len({t["path"] for t in selected}), "lines_recommended": lines, "estimated_source_tokens": max(1, lines * 8), "estimated_resolver_tokens": max(1, len(task) // 4), "estimated_searches": 0 if level == "high" else min(3, len(terms)), "estimated_tool_calls": 1 + len(selected), "estimated_coverage_reduction": "estimate only; compare against benchmark baseline"}}
    errors = validate_schema_json(result, "resolver-result.schema.json")
    if errors: raise ValueError(f"Invalid resolver result: {errors}")
    return result
def format_human(res: dict[str, Any]) -> str:
    return "\n".join([f"# Task Resolution: {res['task']}", f"Confidence: {res['confidence']['level']} ({res['confidence']['score']})", *[f"- `{t['path']}:{t['start_line']}-{t['end_line']}` {t['symbol'] or ''}" for t in res['primary_targets']]])
def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("task"); parser.add_argument("--repo-root",default="."); parser.add_argument("--output"); parser.add_argument("--format",choices=["json","human"],default="human"); a=parser.parse_args(); r=resolve_task(a.repo_root,a.task,a.output); print(json.dumps(r,indent=2) if a.format=="json" else format_human(r)); return 0
if __name__ == "__main__": raise SystemExit(main())
