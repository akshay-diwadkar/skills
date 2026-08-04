from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V7_SOURCE = ROOT / "skills" / "engineering" / "plan-change" / "scripts" / "plan_runtime.py"
V7_CONSUMER = ROOT / "skills" / "engineering" / "implement-plan" / "scripts" / "plan_v7_runtime.py"
V6_FROZEN = ROOT / "skills" / "engineering" / "implement-plan" / "scripts" / "plan_v6_runtime.py"


def test_versioned_plan_runtimes_are_byte_identical_to_their_sources() -> None:
    expected_v7 = V7_SOURCE.read_bytes()
    actual_v7 = V7_CONSUMER.read_bytes()
    assert actual_v7 == expected_v7, (
        "current v7 consumer runtime drifted: "
        f"{V7_CONSUMER} sha256={hashlib.sha256(actual_v7).hexdigest()} != "
        f"{V7_SOURCE} sha256={hashlib.sha256(expected_v7).hexdigest()}"
    )


def test_frozen_v6_reader_is_not_an_unannotated_v7_copy() -> None:
    v6_text = V6_FROZEN.read_text(encoding="utf-8")
    assert "FROZEN Plan-contract v6 compatibility reader" in v6_text
    assert "CONTRACT_VERSION = 6" in v6_text
    assert "CONTRACT_VERSION = 7" not in v6_text
