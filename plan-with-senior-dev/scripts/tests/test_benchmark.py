import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from benchmark import create_blind_pack, load_cases, score_total, summarize, validate_cases


def test_benchmark_manifest_has_eight_valid_cases() -> None:
    cases = load_cases()
    assert len(cases) == 8
    assert validate_cases(cases) == []
    assert {case.tier for case in cases} == {"tiny", "standard", "high-risk"}


def test_critical_error_caps_score() -> None:
    record = {
        "repository_truth": 25,
        "decision_completeness": 25,
        "propagation_constraints": 20,
        "interfaces_logic": 15,
        "tests_rollback_risk": 15,
        "critical_errors": ["fabricated fact"],
    }
    assert score_total(record) == 59


def test_blind_pack_randomizes_and_hides_variant_in_entries(tmp_path: Path) -> None:
    cases = load_cases()
    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    baseline.mkdir()
    candidate.mkdir()
    for case in cases:
        for replicate in (1, 2):
            name = f"{case.case_id}-{replicate}.md"
            (baseline / name).write_text("baseline plan", encoding="utf-8")
            (candidate / name).write_text("candidate plan", encoding="utf-8")
    pack, reveal = create_blind_pack(cases, baseline, candidate, seed=7)
    assert len(pack["entries"]) == 32
    assert all("variant" not in entry for entry in pack["entries"])
    assert "reveal" not in pack
    assert set(reveal.values()) == {"baseline", "candidate"}


def test_summary_reports_candidate_delta() -> None:
    reveal = {"case-1-A": "baseline", "case-1-B": "candidate"}
    scores = [
        {
            "output_id": "case-1-A",
            "repository_truth": 20,
            "decision_completeness": 15,
            "propagation_constraints": 10,
            "interfaces_logic": 10,
            "tests_rollback_risk": 10,
            "one_shot": False,
            "critical_errors": [],
        },
        {
            "output_id": "case-1-B",
            "repository_truth": 25,
            "decision_completeness": 25,
            "propagation_constraints": 20,
            "interfaces_logic": 15,
            "tests_rollback_risk": 15,
            "one_shot": True,
            "critical_errors": [],
        },
    ]
    result = summarize(scores, reveal)
    assert result["baseline"]["median"] == 65
    assert result["candidate"]["median"] == 100
    assert result["delta"]["median"] == 35
    assert result["candidate"]["one_shot_rate"] == 1.0
