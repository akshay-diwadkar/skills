#!/usr/bin/env python3
"""Benchmark knowledge layer against baseline repository exploration modes."""

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

from benchmarking.evaluator import BenchmarkEvaluator

# Backwards compatibility alias
BenchmarkRunner = BenchmarkEvaluator


def format_human_report(res: dict[str, Any]) -> str:
    """Format human-readable benchmark evaluation report."""
    lines = [
        "# Knowledge Layer Retrieval Benchmark Report",
        "",
        "| Mode | Files Opened | Lines Read | Est Input Tokens | MRR | Recall@5 | Precision@5 | nDCG@5 | Latency (ms) |",
        "|---|---|---|---|---|---|---|---|---|",
    ]

    for mode, data in res["summary"].items():
        if data["tasks_evaluated"] > 0:
            lines.append(
                f"| `{mode}` | {data['total_files_opened']} | {data['total_lines_read']} | {data['total_tokens_est']} | "
                f"{data['mean_mrr']} | {data['mean_recall']} | {data['mean_precision']} | {data['mean_ndcg']} | {data['mean_latency_ms']} |"
            )

    lines.extend(
        [
            "",
            "## Task Resolution Metrics",
            "",
        ]
    )

    for d in res["task_details"]:
        lines.append(f"- Task: `{d['task']}`")
        lines.append(f"  - Target Files: {', '.join(f'`{f}`' for f in d['target_files'])}")
        lines.append(
            f"  - Mode 5 Confidence: `{d['mode_5_confidence']}` | MRR: {d['mode_5_mrr']} | Recall: {d['mode_5_recall']}"
        )
        lines.append(f"  - Token Reduction vs Baseline: **{d['token_savings_percent']}%**")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run benchmark evaluation suite.")
    parser.add_argument("--repo-root", default=".", help="Target repository root")
    parser.add_argument("--tasks", required=True, help="Path to benchmark tasks JSON file")
    parser.add_argument("--format", choices=["json", "human"], default="human", help="Output format")
    parser.add_argument("--report-only", action="store_true", help="Report gate failures without a non-zero exit code")

    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()
    tasks_file = Path(args.tasks).resolve()

    evaluator = BenchmarkEvaluator(repo_root, tasks_file)
    res = evaluator.evaluate()

    if args.format == "json":
        print(json.dumps(res, indent=2))
    else:
        print(format_human_report(res))

    return 0 if args.report_only or res.get("gate", {}).get("passed", False) else 2


if __name__ == "__main__":
    sys.exit(main())
