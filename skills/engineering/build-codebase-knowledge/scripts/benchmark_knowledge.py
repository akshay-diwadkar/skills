#!/usr/bin/env python3
"""Benchmark knowledge layer against baseline repository exploration modes."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from resolve_task import resolve_task

def estimate_tokens(text: str) -> int:
    """Documented token estimator: approx 4 characters per token."""
    return max(1, len(text) // 4)

class BenchmarkRunner:
    def __init__(self, repo_root: Path, tasks_file: Path):
        self.repo_root = repo_root
        self.tasks_file = tasks_file
        self.tasks = json.loads(tasks_file.read_text(encoding="utf-8"))

    def run_benchmark(self) -> dict[str, Any]:
        modes = ["A_no_knowledge", "B_markdown_only", "C_index_no_resolver", "D_index_resolver", "E_index_resolver_expansion"]
        summary: dict[str, Any] = {m: {"total_files_opened": 0, "total_lines_read": 0, "total_tokens_est": 0, "mrr_sum": 0.0, "tasks_evaluated": 0} for m in modes}
        details = []

        for task_obj in self.tasks:
            t_name = task_obj["task"]
            target_files = task_obj.get("target_files", [])

            # Run Resolver for Mode D & E
            t0 = time.time()
            res = resolve_task(self.repo_root, t_name)
            t_resolver = (time.time() - t0) * 1000

            candidates = res.get("candidates", [])
            candidate_paths = [c["path"] for c in candidates]

            # Calculate MRR for Mode E
            mrr = 0.0
            for idx, path in enumerate(candidate_paths, start=1):
                if path in target_files:
                    mrr = 1.0 / idx
                    break

            # Mode A: No knowledge -> Reads all files in repo
            all_files = list(self.repo_root.glob("src/**/*.*")) + list(self.repo_root.glob("lib/**/*.*"))
            lines_A = sum(len(f.read_text(errors="ignore").splitlines()) for f in all_files if f.is_file())
            tokens_A = lines_A * 8  # approx 8 tokens per line

            # Mode B: Markdown only
            k_dir = self.repo_root / ".agent" / "knowledge"
            ctx_text = (k_dir / "context.md").read_text(encoding="utf-8") if (k_dir / "context.md").is_file() else ""
            arch_text = (k_dir / "architecture.md").read_text(encoding="utf-8") if (k_dir / "architecture.md").is_file() else ""
            lines_B = len(ctx_text.splitlines()) + len(arch_text.splitlines()) + 300
            tokens_B = estimate_tokens(ctx_text + arch_text) + 2400

            # Mode E: Index + Resolver + Progressive Expansion -> Only read top candidate files
            selected_files = candidate_paths[:4]
            lines_E = 0
            for rel_p in selected_files:
                full_p = self.repo_root / rel_p
                if full_p.is_file():
                    lines_E += len(full_p.read_text(errors="ignore").splitlines())
            tokens_E = lines_E * 8 + estimate_tokens(json.dumps(res))

            # Aggregate stats
            summary["A_no_knowledge"]["total_files_opened"] += len(all_files)
            summary["A_no_knowledge"]["total_lines_read"] += lines_A
            summary["A_no_knowledge"]["total_tokens_est"] += tokens_A
            summary["A_no_knowledge"]["tasks_evaluated"] += 1

            summary["E_index_resolver_expansion"]["total_files_opened"] += len(selected_files)
            summary["E_index_resolver_expansion"]["total_lines_read"] += lines_E
            summary["E_index_resolver_expansion"]["total_tokens_est"] += tokens_E
            summary["E_index_resolver_expansion"]["mrr_sum"] += mrr
            summary["E_index_resolver_expansion"]["tasks_evaluated"] += 1

            details.append({
                "task": t_name,
                "target_files": target_files,
                "mode_E_mrr": mrr,
                "mode_E_candidates": selected_files,
                "mode_A_tokens": tokens_A,
                "mode_E_tokens": tokens_E,
                "token_savings_percent": round((1 - (tokens_E / max(tokens_A, 1))) * 100, 2),
                "resolver_time_ms": round(t_resolver, 2)
            })

        for m in modes:
            count = max(summary[m]["tasks_evaluated"], 1)
            summary[m]["mean_mrr"] = round(summary[m]["mrr_sum"] / count, 3)

        return {"summary": summary, "task_details": details}

def format_human_report(res: dict[str, Any]) -> str:
    lines = [
        "# Knowledge Layer Benchmark Report",
        "",
        "| Mode | Files Opened | Lines Read | Est Input Tokens | Mean Reciprocal Rank (MRR) |",
        "|---|---|---|---|---|",
    ]
    for mode, data in res["summary"].items():
        if data["tasks_evaluated"] > 0:
            lines.append(f"| `{mode}` | {data['total_files_opened']} | {data['total_lines_read']} | {data['total_tokens_est']} | {data.get('mean_mrr', 0.0)} |")

    lines.extend([
        "",
        "## Task Details",
        "",
    ])
    for d in res["task_details"]:
        lines.append(f"- Task: `{d['task']}`")
        lines.append(f"  - MRR: {d['mode_E_mrr']}")
        lines.append(f"  - Token Savings: {d['token_savings_percent']}% reduction vs baseline")

    return "\n".join(lines)

def main() -> int:
    parser = argparse.ArgumentParser(description="Run benchmark suite.")
    parser.add_argument("--repo-root", default=".", help="Target repository root")
    parser.add_argument("--tasks", required=True, help="Path to benchmark tasks JSON fixture")
    parser.add_argument("--format", choices=["json", "human"], default="human", help="Output format")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    tasks_file = Path(args.tasks).resolve()

    runner = BenchmarkRunner(repo_root, tasks_file)
    res = runner.run_benchmark()

    if args.format == "json":
        print(json.dumps(res, indent=2))
    else:
        print(format_human_report(res))
    return 0

if __name__ == "__main__":
    sys.exit(main())
