from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks import run_full, run_representative
from benchmarks.gates import evaluate_balanced_gates
from benchmarks.loader import (
    FixtureLeakageError,
    assert_split_independence,
    load_case_splits,
)
from benchmarks.metrics import aggregate_benchmark_metrics

pytestmark = pytest.mark.benchmark


def test_adversarial_and_heldout_fixtures_are_hash_bound_and_independent() -> None:
    splits = load_case_splits()
    assert len(splits["tuning"]) >= 10
    assert len(splits["heldout"]) >= 6
    assert {case.split for case in splits["tuning"]} == {"tuning"}
    assert {case.split for case in splits["heldout"]} == {"heldout"}
    assert any("abstention" in case.tags for case in splits["heldout"])
    assert any("multi-owner" in case.tags for case in splits["tuning"])


def test_duplicate_query_across_splits_is_rejected() -> None:
    splits = load_case_splits()
    duplicate = [splits["heldout"][0], *splits["tuning"]]
    duplicate[0] = duplicate[0].__class__(
        **{**duplicate[0].__dict__, "query": splits["tuning"][0].query}
    )
    with pytest.raises(FixtureLeakageError):
        assert_split_independence(splits["tuning"], duplicate)


def test_phase_metrics_do_not_mix_constraints_or_impacts_into_owner_precision() -> None:
    metrics = aggregate_benchmark_metrics(
        [
            {
                "task_id": "separated",
                "expected_owner_sets": [["owner.py"]],
                "primary_owner": {"path": "owner.py"},
                "co_owners": [],
                "alternatives": [{"path": "alternative.py"}],
                "expected_constraints": ["config.yaml"],
                "constraints": [{"path": "wrong-config.yaml"}],
                "expected_impacts": ["caller.py"],
                "impacts": [{"path": "caller.py"}],
                "expected_status": "resolved",
                "status": "resolved",
                "confidence_level": "high",
            }
        ]
    )
    assert metrics["phase1"]["primary_owner_precision"] == 1.0
    assert metrics["phase1"]["exact_owner_set_match"] == 1.0
    assert metrics["phase2"]["precision"] == 0.0
    assert metrics["phase2"]["recall"] == 0.0
    assert metrics["phase3"]["precision"] == 1.0
    assert metrics["phase3"]["recall"] == 1.0


def test_phase1_metrics_score_cardinality_false_primary_and_abstention() -> None:
    metrics = aggregate_benchmark_metrics(
        [
            {
                "task_id": "multi",
                "expected_owner_sets": [["a.py", "b.py"]],
                "primary_owner": {"path": "a.py"},
                "co_owners": [{"path": "wrong.py"}],
                "alternatives": [{"path": "b.py"}],
                "expected_status": "resolved",
                "status": "ambiguous",
                "confidence_level": "medium",
            },
            {
                "task_id": "empty",
                "expected_owner_sets": [],
                "primary_owner": None,
                "co_owners": [],
                "alternatives": [],
                "expected_status": "abstain",
                "status": "abstain",
                "confidence_level": "low",
            },
        ]
    )["phase1"]
    assert metrics["hit_at_1"] == 1.0
    assert metrics["hit_at_3"] == 1.0
    assert metrics["primary_owner_precision"] == pytest.approx(0.5)
    assert metrics["primary_owner_recall"] == pytest.approx(0.5)
    assert metrics["exact_owner_set_match"] == 0.5
    assert metrics["false_primary_rate"] == 0.0
    assert metrics["abstention_precision"] == 1.0
    assert metrics["abstention_recall"] == 1.0


def test_balanced_gates_apply_safety_and_ownership_to_heldout_independently() -> None:
    passing_phase1 = {
        "hit_at_1": 1.0,
        "hit_at_3": 1.0,
        "mrr": 1.0,
        "primary_owner_precision": 1.0,
        "primary_owner_recall": 1.0,
        "exact_owner_set_match": 1.0,
        "false_primary_rate": 0.0,
        "abstention_precision": 1.0,
        "abstention_recall": 1.0,
        "incorrect_high_confidence": 0,
    }
    aggregate = {
        "phase1": passing_phase1,
        "phase2": {"precision": 1.0, "recall": 1.0},
        "phase3": {"precision": 1.0, "recall": 1.0},
    }
    heldout = {**aggregate, "phase1": {**passing_phase1, "hit_at_1": 0.5}}
    gates = evaluate_balanced_gates(aggregate, heldout=heldout)
    assert gates["hit_at_1"] is True
    assert gates["heldout_hit_at_1"] is False


def test_phase_gates_are_not_fabricated_when_ground_truth_is_absent() -> None:
    metrics = aggregate_benchmark_metrics(
        [
            {
                "expected_owner_sets": [["owner.py"]],
                "primary_owner": {"path": "owner.py"},
                "expected_status": "resolved",
                "status": "resolved",
                "confidence_level": "high",
                "constraints": [{"path": "config.py"}],
                "impacts": [{"path": "caller.py"}],
            }
        ]
    )
    assert metrics["phase2"]["ground_truth_available"] is False
    assert metrics["phase3"]["ground_truth_available"] is False
    gates = evaluate_balanced_gates(metrics)
    assert gates["constraint_precision"] is True
    assert gates["impact_precision"] is True


def test_runtime_resolver_has_no_benchmark_fixture_dependency() -> None:
    resolver_root = (
        ROOT
        / "skills"
        / "engineering"
        / "map-codebase"
        / "scripts"
        / "resolver"
    )
    paths = list(resolver_root.glob("*.py"))
    paths.append(
        ROOT / "skills" / "engineering" / "map-codebase" / "scripts" / "resolve_task.py"
    )
    for path in paths:
        source = path.read_text(encoding="utf-8")
        assert "from benchmarks" not in source
        assert "import benchmarks" not in source
        assert "fixtures/" not in source.replace("\\", "/")


@pytest.mark.parametrize("module", [run_full, run_representative])
def test_module_benchmark_entrypoints_return_gate_status(
    module: object, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    class Runner:
        @staticmethod
        def evaluate(profile: str) -> dict[str, object]:
            assert profile in {"full", "representative"}
            return {"all_gates_pass": True, "profile": profile}

    monkeypatch.setattr(module, "_runner", lambda: Runner)
    assert module.main() == 0  # type: ignore[attr-defined]
    assert '"all_gates_pass": true' in capsys.readouterr().out
