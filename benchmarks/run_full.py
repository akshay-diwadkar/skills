from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "benchmarks" / "reports"


def _runner() -> ModuleType:
    path = ROOT / "tests" / "skills" / "map-codebase" / "benchmark_runner.py"
    spec = importlib.util.spec_from_file_location("map_codebase_benchmark_runner", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load benchmark runner: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_report(result: dict[str, Any], profile: str, runner: ModuleType) -> None:
    if "metrics" not in result:
        return
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / f"after-{profile}.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if profile == "full":
        (REPORTS / "after-full.md").write_text(runner.render_markdown(result), encoding="utf-8")
        resolver = result["metrics"]["resolver"]
        split_metrics = result.get("split_results", {})
        heldout = split_metrics.get("heldout", {}).get("metrics", {}).get("phase1", {})
        comparison = [
            "# Resolver Before/After",
            "",
            "The historical owner precision mixed all three phases and is not directly comparable to primary-owner precision.",
            "",
            "| Metric | Before | After | Held-out |",
            "| --- | ---: | ---: | ---: |",
            f"| Hit@1 | 0.806 | {resolver['hit_at_1']:.3f} | {heldout.get('hit_at_1', 0):.3f} |",
            f"| Hit@3 | 0.972 | {resolver['hit_at_3']:.3f} | {heldout.get('hit_at_3', 0):.3f} |",
            f"| MRR | 0.884 | {resolver['mrr']:.3f} | {heldout.get('mrr', 0):.3f} |",
            f"| Primary-owner precision | legacy 0.364 | {resolver['primary_owner_precision']:.3f} | "
            f"{heldout.get('primary_owner_precision', 0):.3f} |",
            f"| Primary-owner recall | legacy 0.780 | {resolver['primary_owner_recall']:.3f} | "
            f"{heldout.get('primary_owner_recall', 0):.3f} |",
            "",
            "Runtime IDF is derived only from the repository being resolved. Resolver modules do not import fixtures; "
            "tuning and held-out cases are hash-bound and reported separately.",
        ]
        (REPORTS / "comparison.md").write_text("\n".join(comparison) + "\n", encoding="utf-8")


def main() -> int:
    runner = _runner()
    result = runner.evaluate("full")
    write_report(result, "full", runner)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["all_gates_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
