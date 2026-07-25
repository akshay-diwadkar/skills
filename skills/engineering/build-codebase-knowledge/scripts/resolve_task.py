#!/usr/bin/env python3
"""Deterministic Task Resolver entry point."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Ensure skill scripts directory is on sys.path
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from knowledge.config import load_config
from resolver.confidence import estimate_confidence
from resolver.expansion import progressive_expand
from resolver.intent import classify_intent
from resolver.read_plan import generate_read_plan
from resolver.scoring import score_candidates
from resolver.signals import extract_signals


def load_knowledge_index(repo_root: Path | str, knowledge_dir: Path | str | None = None) -> dict[str, Any]:
    """Load index.json and manifest.json from knowledge directory."""
    root = Path(repo_root).resolve()
    config = load_config(root)
    k_dir = Path(knowledge_dir).resolve() if knowledge_dir else root / config["output_dir"]

    index_file = k_dir / "index.json"
    manifest_file = k_dir / "manifest.json"

    if not index_file.is_file():
        raise FileNotFoundError(f"Knowledge index not found at {index_file}. Run build-codebase-knowledge build first.")

    index_data = json.loads(index_file.read_text(encoding="utf-8"))
    manifest_data = json.loads(manifest_file.read_text(encoding="utf-8")) if manifest_file.is_file() else {}
    return {"index": index_data, "manifest": manifest_data, "dir": k_dir, "config": config}


class ConfidenceString(str):
    def __getitem__(self, key: Any) -> Any:
        if key == "level":
            return str(self)
        return super().__getitem__(key)


def resolve_task(
    repo_root: Path | str,
    task: str,
    knowledge_dir: Path | str | None = None,
) -> dict[str, Any]:
    """Execute 7-stage deterministic task resolution pipeline."""
    root = Path(repo_root).resolve()
    knowledge = load_knowledge_index(root, knowledge_dir)
    config = knowledge["config"]
    index_data = knowledge["index"]
    manifest_data = knowledge["manifest"]
    freshness_state = manifest_data.get("freshness_state", "fresh")

    # Stage A: Signal Extraction
    signals = extract_signals(task, index_data)

    # Stage B: Intent Classification
    intents = classify_intent(task)

    # Stage C & D: Candidate Generation & Weighted Scoring
    scored_candidates = score_candidates(signals, intents, index_data, config)

    # Stage E: Confidence Estimation
    confidence_str, confidence_reasons = estimate_confidence(scored_candidates, signals, freshness_state)
    confidence = ConfidenceString(confidence_str)

    # Stage F: Progressive Expansion
    expanded_candidates, expansion_stop_reason = progressive_expand(scored_candidates, confidence_str, index_data)

    # Stage G: Read Plan Generation
    plan = generate_read_plan(expanded_candidates, index_data)

    return {
        "status": "success",
        "task": task,
        "signals": signals,
        "intents": intents,
        "confidence": confidence,
        "confidence_reasons": confidence_reasons,
        "expansion_stop_reason": expansion_stop_reason,
        "candidates": plan["read_sequence"],
        "phases": plan["phases"],
        "skip_list": plan["skip_list"],
        "source_verification_required": True,
        "source_validation_required": True,
    }


def format_human(res: dict[str, Any]) -> str:
    """Format human-readable task resolution report."""
    lines = [
        f"# Task Resolution Plan: `{res['task']}`",
        "",
        f"- **Confidence**: `{res['confidence'].upper()}` ({', '.join(res['confidence_reasons'])})",
        f"- **Intents Classified**: {', '.join(res['intents'])}",
        f"- **Expansion Status**: {res['expansion_stop_reason']}",
        f"- **Source Verification Required**: {res['source_verification_required']}",
        "",
        "## Recommended Read Sequence",
        "",
        "| Order | Score | Role | Subsystem | Path | Evidence Reasons |",
        "|---|---|---|---|---|---|",
    ]

    for cand in res["candidates"]:
        reasons_str = "; ".join(cand.get("reasons", []))
        lines.append(f"| {cand['read_order']} | {cand['score']} | {cand['role']} | {cand['subsystem']} | `{cand['path']}` | {reasons_str} |")

    lines.extend([
        "",
        "## Phased Execution Plan",
    ])
    for phase in res["phases"]:
        files_str = ", ".join(f"`{f}`" for f in phase["files"]) if phase["files"] else "None"
        lines.append(f"{phase['phase']}. **{phase['title']}**: {files_str}")

    lines.extend([
        "",
        "## Explicit Skip List",
    ])
    for skip in res["skip_list"]:
        lines.append(f"- `{skip}`")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve natural language task.")
    parser.add_argument("task", nargs="?", help="Task description string")
    parser.add_argument("--task-file", help="File containing task description")
    parser.add_argument("--repo-root", default=".", help="Target repository root")
    parser.add_argument("--output", help="Knowledge directory")
    parser.add_argument("--format", choices=["json", "human"], default="human", help="Output format")

    args = parser.parse_args()
    t_str = args.task
    if args.task_file:
        t_str = Path(args.task_file).read_text(encoding="utf-8").strip()

    if not t_str:
        print("Error: task string or --task-file required", file=sys.stderr)
        return 1

    repo_root = Path(args.repo_root).resolve()
    k_dir = Path(args.output).resolve() if args.output else None

    res = resolve_task(repo_root, t_str, k_dir)
    if args.format == "json":
        print(json.dumps(res, indent=2))
    else:
        print(format_human(res))

    return 0


if __name__ == "__main__":
    sys.exit(main())
