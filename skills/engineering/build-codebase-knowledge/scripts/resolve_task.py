#!/usr/bin/env python3
"""Deterministic Task Resolver engine."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

def load_knowledge_index(repo_root: Path, knowledge_dir: Path | None = None) -> dict[str, Any]:
    k_dir = knowledge_dir if knowledge_dir else repo_root / ".agent" / "knowledge"
    index_file = k_dir / "index.json"
    manifest_file = k_dir / "manifest.json"
    if not index_file.is_file():
        raise FileNotFoundError(f"Knowledge index not found at {index_file}. Run build-codebase-knowledge build first.")

    index_data = json.loads(index_file.read_text(encoding="utf-8"))
    manifest_data = json.loads(manifest_file.read_text(encoding="utf-8")) if manifest_file.is_file() else {}
    return {"index": index_data, "manifest": manifest_data, "dir": k_dir}

class TaskResolverPipeline:
    def __init__(self, repo_root: Path, task: str, knowledge: dict[str, Any]):
        self.repo_root = repo_root
        self.task = task
        self.index = knowledge["index"]
        self.manifest = knowledge["manifest"]
        self.knowledge_state = self.manifest.get("freshness_state", "fresh")
        self.revision = self.manifest.get("repository", {}).get("revision", "")

    def run(self) -> dict[str, Any]:
        return self.execute()

    def stage_a_extract_signals(self) -> dict[str, list[str]]:
        # Preserve exact symbols, paths, case
        identifiers = re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_\./\\]*\.[a-zA-Z0-9_]+\b|\b[a-zA-Z_][a-zA-Z0-9_]{3,}\b", self.task)
        paths = re.findall(r"[a-zA-Z0-9_\-\./\\]+\.[a-zA-Z0-9_]+", self.task)
        actions = re.findall(r"(?i)\b(add|create|update|fix|refactor|remove|delete|optimize|test|configure)\b", self.task)
        domains = re.findall(r"(?i)\b(auth|session|password|reset|rate|limit|user|account|billing|worker|api)\b", self.task)

        return {
            "identifiers": list(set(identifiers + paths)),
            "domains": list(set([d.lower() for d in domains])),
            "actions": list(set([a.lower() for a in actions])),
        }

    def stage_b_classify_intent(self) -> list[str]:
        t_lower = self.task.lower()
        intents = []
        if any(k in t_lower for k in ["fix", "bug", "issue", "error", "crash", "fault"]):
            intents.append("bug")
        if any(k in t_lower for k in ["add", "feature", "create", "implement", "support"]):
            intents.append("feature")
        if any(k in t_lower for k in ["rate limit", "security", "auth", "permission", "password"]):
            intents.append("security")
        if any(k in t_lower for k in ["test", "coverage", "spec"]):
            intents.append("tests")
        if any(k in t_lower for k in ["config", "setting", "env", "yaml", "toml"]):
            intents.append("configuration")
        if any(k in t_lower for k in ["refactor", "clean", "structure"]):
            intents.append("refactor")
        return intents if intents else ["feature"]

    def stage_c_d_score_candidates(self, signals: dict[str, list[str]], intents: list[str]) -> list[dict[str, Any]]:
        candidates = []
        files = self.index.get("files", [])
        symbols = self.index.get("symbols", [])
        entry_points = [ep["path"] for ep in self.index.get("entry_points", [])]

        task_words = [w.lower() for w in re.findall(r"\b\w+\b", self.task)]

        for f in files:
            path = f["path"]
            score = 0.0
            reasons = []
            matched_symbols = []

            # 1. Exact path match
            for idf in signals["identifiers"]:
                if idf in path:
                    score += 10.0
                    reasons.append(f"exact path match: {idf}")

            # 2. Exact symbol match
            for sym in f.get("symbols", []):
                for idf in signals["identifiers"]:
                    if idf.lower() == sym.lower() or idf == sym:
                        score += 10.0
                        matched_symbols.append(sym)
                        reasons.append(f"exact symbol match: {sym}")

            # 3. Filename match
            stem = Path(path).stem.lower()
            for word in task_words:
                if len(word) > 3 and word in stem:
                    score += 7.0
                    reasons.append(f"filename match: {word}")

            # 4. Subsystem & Keyword / Symbol substring match
            for domain in signals["domains"]:
                if domain in f.get("subsystem", "").lower() or domain in path.lower():
                    score += 5.0
                    reasons.append(f"subsystem match: {domain}")
                if any(domain in sym.lower() for sym in f.get("symbols", [])):
                    score += 5.0
                    reasons.append(f"symbol domain match: {domain}")
                if any(domain in kw.lower() for kw in f.get("keywords", [])):
                    score += 3.0
                    reasons.append(f"keyword match: {domain}")

            # 5. Entry point proximity
            if path in entry_points:
                score += 4.0
                reasons.append("entry point proximity")

            # 6. Test relationship
            if "tests" in intents and f.get("role") == "test":
                score += 4.0
                reasons.append("test intent match")

            # 7. Config relationship
            if "configuration" in intents and f.get("role") == "configuration":
                score += 4.0
                reasons.append("config intent match")

            # Penalties
            if path in self.index.get("generated_paths", []):
                score -= 8.0
                reasons.append("penalty: generated code")
            if "vendor" in path.lower() or "node_modules" in path.lower():
                score -= 10.0
                reasons.append("penalty: vendor code")

            if score > 0:
                normalized_score = min(round(score / 25.0, 2), 1.0)
                candidates.append({
                    "path": path,
                    "kind": f.get("role", "source"),
                    "score": normalized_score,
                    "raw_score": score,
                    "reasons": list(set(reasons)),
                    "symbols": matched_symbols,
                    "read_order": 0
                })

        candidates.sort(key=lambda x: x["raw_score"], reverse=True)
        return candidates

    def stage_e_estimate_confidence(self, candidates: list[dict[str, Any]], signals: dict[str, list[str]]) -> tuple[str, list[str]]:
        reasons = []
        if not candidates:
            return "low", ["no matching candidate files found in index"]

        top_score = candidates[0]["raw_score"]
        exact_matches = [c for c in candidates if any("exact" in r for r in c["reasons"])]

        if exact_matches or top_score >= 15.0:
            reasons.append("exact identifier match confirmed")
            reasons.append("multiple independent signals agree")
            return "high", reasons
        elif top_score >= 8.0:
            reasons.append("subsystem and filename signals match")
            return "medium", reasons
        else:
            reasons.append("weak signal agreement; expansion required")
            return "low", reasons

    def stage_f_g_expand_and_plan(self, candidates: list[dict[str, Any]], confidence: str) -> tuple[list[dict[str, Any]], list[str], list[str]]:
        if confidence == "high":
            selected = candidates[:4]
        elif confidence == "medium":
            selected = candidates[:8]
        else:
            selected = candidates[:15]

        # Assign read order
        for idx, item in enumerate(selected, start=1):
            item["read_order"] = idx

        # Extract tests & config
        tests = [c["path"] for c in selected if c["kind"] == "test"]
        configs = [c["path"] for c in selected if c["kind"] == "configuration"]
        if not tests:
            tests = [t["path"] for t in self.index.get("tests", [])[:2]]
        if not configs:
            configs = [c["path"] for c in self.index.get("configurations", [])[:2]]

        excluded = ["vendor/", "node_modules/", "dist/", "generated/"]
        return selected, tests, configs

    def execute(self) -> dict[str, Any]:
        signals = self.stage_a_extract_signals()
        intents = self.stage_b_classify_intent()
        candidates = self.stage_c_d_score_candidates(signals, intents)
        confidence_level, confidence_reasons = self.stage_e_estimate_confidence(candidates, signals)
        selected_candidates, tests, configs = self.stage_f_g_expand_and_plan(candidates, confidence_level)

        matched_subsystems = list(set([c["path"].split("/")[0] for c in selected_candidates if "/" in c["path"]]))

        return {
            "task": self.task,
            "knowledge": {
                "state": self.knowledge_state,
                "revision": self.revision,
                "warnings": [] if self.knowledge_state == "fresh" else ["Index may be partially stale"],
            },
            "intent": intents,
            "signals": signals,
            "confidence": {
                "level": confidence_level,
                "reasons": confidence_reasons
            },
            "subsystems": matched_subsystems if matched_subsystems else ["root"],
            "candidates": selected_candidates,
            "tests": tests,
            "configuration": configs,
            "recommended_searches": [f"grep '{sig}'" for sig in signals["identifiers"][:3]],
            "excluded_areas": ["vendor/", "node_modules/", "dist/"],
            "unknowns": ["Verify behavior in source code before editing"],
            "source_validation_required": True
        }

def resolve_task(repo_root: Path, task: str, knowledge_dir: Path | None = None) -> dict[str, Any]:
    knowledge = load_knowledge_index(repo_root, knowledge_dir)
    pipeline = TaskResolverPipeline(repo_root, task, knowledge)
    return pipeline.execute()

def format_human(res: dict[str, Any]) -> str:
    lines = [
        f"Knowledge: {res['knowledge']['state']}",
        f"Confidence: {res['confidence']['level']}",
        f"Subsystem: {', '.join(res['subsystems'])}",
        "",
        "Read:",
    ]
    for c in res["candidates"]:
        lines.append(f"{c['read_order']}. `{c['path']}`")
        for r in c["reasons"]:
            lines.append(f"   - {r}")

    lines.extend([
        "",
        "Skip:",
        "- `vendor/`: excluded",
        "- `dist/`: excluded",
        "",
        "Verify behavior in source before implementation.",
    ])
    return "\n".join(lines)

def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve natural language engineering task.")
    parser.add_argument("--repo-root", default=".", help="Target repository root")
    parser.add_argument("--task", help="Natural language task description")
    parser.add_argument("--task-file", help="Path to text file containing task description")
    parser.add_argument("--format", choices=["json", "human"], default="human", help="Output format")
    args = parser.parse_args()

    task_str = args.task
    if args.task_file:
        task_str = Path(args.task_file).read_text(encoding="utf-8").strip()

    if not task_str:
        print("Error: Must provide --task or --task-file", file=sys.stderr)
        return 1

    repo_root = Path(args.repo_root).resolve()
    try:
        res = resolve_task(repo_root, task_str)
        if args.format == "json":
            print(json.dumps(res, indent=2))
        else:
            print(format_human(res))
    except Exception as e:
        print(f"Resolver error: {e}", file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
