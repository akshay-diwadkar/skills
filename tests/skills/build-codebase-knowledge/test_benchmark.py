import sys
from pathlib import Path

SKILL_SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "engineering" / "build-codebase-knowledge" / "scripts"
if str(SKILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SKILL_SCRIPTS))

from benchmark_knowledge import BenchmarkRunner
from build_knowledge import build_knowledge


def test_benchmark_runner(sample_repo: Path):
    out_dir = sample_repo / ".agent" / "knowledge"
    build_knowledge(sample_repo, out_dir)

    tasks_file = Path(__file__).parent / "fixtures" / "benchmark_tasks.json"
    runner = BenchmarkRunner(sample_repo, tasks_file)
    res = runner.run_benchmark()

    assert "summary" in res
    assert "E_index_resolver_expansion" in res["summary"]
    assert res["summary"]["E_index_resolver_expansion"]["tasks_evaluated"] > 0
