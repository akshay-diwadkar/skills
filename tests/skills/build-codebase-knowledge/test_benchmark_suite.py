import sys
from pathlib import Path

SKILL_SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "engineering" / "build-codebase-knowledge" / "scripts"
if str(SKILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SKILL_SCRIPTS))

from benchmarking.evaluator import BenchmarkEvaluator
from build_knowledge import build_knowledge


def test_benchmark_evaluator_all_modes(tmp_path: Path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "service.py").write_text("class PasswordResetService:\n    pass\n", encoding="utf-8")

    out_dir = tmp_path / ".agent" / "knowledge"
    build_knowledge(tmp_path, out_dir)

    fixture_path = Path(__file__).resolve().parent / "fixtures" / "benchmark_tasks.json"
    evaluator = BenchmarkEvaluator(tmp_path, fixture_path)
    res = evaluator.evaluate()

    assert "summary" in res
    assert len(res["summary"]) >= 5
    for mode_name, mode_stats in res["summary"].items():
        assert mode_stats["tasks_evaluated"] > 0
        assert "mean_mrr" in mode_stats
        assert "mean_recall" in mode_stats
