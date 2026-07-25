"""Benchmark evaluator runner across all declared modes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from benchmarking.retrieval_modes import (
    run_mode_baseline_targeted_search,
    run_mode_index_and_resolver,
    run_mode_index_only,
    run_mode_index_resolver_progressive,
    run_mode_markdown_orientation,
)


class BenchmarkEvaluator:
    def __init__(self, repo_root: Path, tasks_file: Path):
        self.repo_root = repo_root
        self.tasks_file = tasks_file
        self.tasks = json.loads(tasks_file.read_text(encoding="utf-8"))

    def evaluate(self) -> dict[str, Any]:
        modes = [
            "baseline_targeted_search",
            "markdown_orientation",
            "index_only",
            "index_and_resolver",
            "index_resolver_progressive",
        ]
        summary: dict[str, Any] = {
            m: {
                "total_files_opened": 0,
                "total_lines_read": 0,
                "total_tokens_est": 0,
                "mrr_sum": 0.0,
                "recall_sum": 0.0,
                "precision_sum": 0.0,
                "ndcg_sum": 0.0,
                "latency_sum_ms": 0.0,
                "tasks_evaluated": 0,
            }
            for m in modes
        }

        details = []

        for task_obj in self.tasks:
            t_name = task_obj["task"]
            target_files = task_obj.get("target_files", [])

            # Run all 5 retrieval modes
            m1 = run_mode_baseline_targeted_search(self.repo_root, target_files)
            m2 = run_mode_markdown_orientation(self.repo_root, target_files)
            m3 = run_mode_index_only(self.repo_root, target_files)
            m4 = run_mode_index_and_resolver(self.repo_root, t_name, target_files)
            m5 = run_mode_index_resolver_progressive(self.repo_root, t_name, target_files)

            mode_results = [m1, m2, m3, m4, m5]
            for m_res in mode_results:
                m_name = m_res["mode"]
                summary[m_name]["total_files_opened"] += m_res["files_opened"]
                summary[m_name]["total_lines_read"] += m_res["lines_read"]
                summary[m_name]["total_tokens_est"] += m_res["tokens_est"]
                summary[m_name]["mrr_sum"] += m_res["mrr"]
                summary[m_name]["recall_sum"] += m_res["recall_at_k"]
                summary[m_name]["precision_sum"] += m_res["precision_at_k"]
                summary[m_name]["ndcg_sum"] += m_res["ndcg_at_k"]
                summary[m_name]["latency_sum_ms"] += m_res["latency_ms"]
                summary[m_name]["tasks_evaluated"] += 1

            token_reduction = round((1.0 - (m5["tokens_est"] / max(m1["tokens_est"], 1))) * 100.0, 2)

            details.append(
                {
                    "task": t_name,
                    "target_files": target_files,
                    "mode_1_baseline_tokens": m1["tokens_est"],
                    "mode_5_progressive_tokens": m5["tokens_est"],
                    "token_savings_percent": token_reduction,
                    "mode_5_mrr": m5["mrr"],
                    "mode_5_recall": m5["recall_at_k"],
                    "mode_5_confidence": m5.get("confidence", "medium"),
                }
            )

        for m in modes:
            count = max(summary[m]["tasks_evaluated"], 1)
            summary[m]["mean_mrr"] = round(summary[m]["mrr_sum"] / count, 4)
            summary[m]["mean_recall"] = round(summary[m]["recall_sum"] / count, 4)
            summary[m]["mean_precision"] = round(summary[m]["precision_sum"] / count, 4)
            summary[m]["mean_ndcg"] = round(summary[m]["ndcg_sum"] / count, 4)
            summary[m]["mean_latency_ms"] = round(summary[m]["latency_sum_ms"] / count, 2)

        # Map legacy mode key aliases for backwards compatibility
        summary["E_index_resolver_expansion"] = summary["index_resolver_progressive"]
        summary["A_no_knowledge"] = summary["baseline_targeted_search"]

        progressive = summary["index_resolver_progressive"]
        baseline = summary["baseline_targeted_search"]
        reduction = 1 - progressive["total_tokens_est"] / max(baseline["total_tokens_est"], 1)
        coverage = sum(1 for detail in details if detail["mode_5_recall"] >= 1.0) / max(len(details), 1)
        gate = {
            "required_file_coverage_at_10": round(coverage, 4),
            "planned_context_reduction": round(reduction, 4),
            "required_coverage": 0.90,
            "required_reduction": 0.60,
            "passed": coverage >= 0.90 and reduction >= 0.60,
        }
        return {"summary": summary, "task_details": details, "gate": gate}

    def run_benchmark(self) -> dict[str, Any]:
        """Backwards compatibility runner method."""
        return self.evaluate()
