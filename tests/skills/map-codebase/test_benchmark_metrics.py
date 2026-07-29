from __future__ import annotations

import socket
import sys
import urllib.request
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from benchmark_runner import (
    _aggregate,
    _case_outcome,
    _credited_savings,
    _patch_metrics,
    _rank_score,
)
from tokenizer import count_tokens

pytestmark = pytest.mark.benchmark


def test_rank_metrics_cover_hits_alternatives_and_misses() -> None:
    assert _rank_score({"a.py", "alternative.py"}, ["alternative.py"]) == (True, True, 1.0)
    assert _rank_score({"a.py"}, ["x.py", "a.py"]) == (False, True, 0.5)
    assert _rank_score({"a.py"}, ["x.py", "y.py", "z.py"]) == (False, False, 0.0)


def test_case_outcome_accepts_hash_bound_alternative_owner_sets() -> None:
    task = {
        "id": "alternative",
        "expected": {
            "primary_owners": [{"path": "canonical.py", "role": "source"}],
            "secondary_surfaces": [],
            "abstain": False,
        },
        "allowed_alternatives": [
            [{"path": "adapter.py", "role": "source", "sha256": "0" * 64}]
        ],
    }
    outcome = _case_outcome(
        "resolver",
        task,
        "Find the behavior owner.",
        [{"path": "adapter.py", "role": "source"}],
        [{"path": "adapter.py", "role": "source"}],
        "",
        "high",
        100,
        [],
    )
    assert outcome["hit_at_1"] is True


def test_patch_metrics_handle_zero_success_and_failed_attempt_tokens() -> None:
    metrics = _patch_metrics(
        [
            {
                "condition": condition,
                "success": condition == "inventory",
                "tokens": 20,
                "characters": 40,
                "bytes": 40,
            }
            for condition in ("resolver", "ripgrep", "inventory")
        ]
    )
    assert metrics["resolver"]["tokens_per_success"] is None
    assert metrics["resolver"]["failed_attempt_tokens"] == 20
    assert metrics["inventory"]["tokens_per_success"] == 20
    assert metrics["inventory"]["failed_attempt_tokens"] == 0


def test_incorrect_outcomes_receive_no_credited_efficiency_savings() -> None:
    assert _credited_savings(True, 20, 100) == pytest.approx(0.8)
    assert _credited_savings(False, 1, 100) == 0.0
    assert _credited_savings(True, 1, 0) == 0.0


def test_offline_tokenization_never_opens_a_network_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def blocked(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("offline tokenization attempted network access")

    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(urllib.request, "urlopen", blocked)
    assert count_tokens("") == 0
    assert count_tokens("hello world") == 2


def test_role_and_abstention_metrics_count_false_positives() -> None:
    task = {
        "allowed_alternatives": [],
        "expected": {
            "primary_owners": [{"path": "owner.py", "role": "source"}],
            "secondary_surfaces": [],
        }
    }
    outcome = {
        "_task": task,
        "expected_abstain": False,
        "abstained": True,
        "hit_at_1": False,
        "hit_at_3": False,
        "reciprocal_rank": 0.0,
        "predicted_primary": ["wrong.json"],
        "predicted_primary_roles": {"wrong.json": "configuration"},
        "owner_true_positive": 0,
        "owner_predicted": 1,
        "owner_expected": 1,
        "incorrect_high_confidence": False,
        "tokens": 7,
        "characters": 9,
        "bytes": 9,
    }
    metrics = _aggregate([outcome])
    assert metrics["roles"]["source"]["fn"] == 1
    assert metrics["roles"]["configuration"]["fp"] == 1
    assert metrics["owner_precision"] == 0.0
    assert metrics["owner_recall"] == 0.0
