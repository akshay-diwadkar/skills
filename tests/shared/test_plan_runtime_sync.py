from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V7_SOURCE = ROOT / "skills" / "engineering" / "plan-change" / "scripts" / "plan_runtime.py"
V7_CONSUMER = ROOT / "skills" / "engineering" / "implement-plan" / "scripts" / "plan_v7_runtime.py"
V6_CONSUMER = ROOT / "skills" / "engineering" / "implement-plan" / "scripts" / "plan_v6_runtime.py"


def test_versioned_plan_runtimes_are_byte_identical_to_their_sources() -> None:
    expected_v7 = V7_SOURCE.read_bytes()
    actual_v7 = V7_CONSUMER.read_bytes()
    assert actual_v7 == expected_v7, (
        "current v7 consumer runtime drifted: "
        f"{V7_CONSUMER} sha256={hashlib.sha256(actual_v7).hexdigest()} != "
        f"{V7_SOURCE} sha256={hashlib.sha256(expected_v7).hexdigest()}"
    )


def test_frozen_v6_runtime_remains_present_and_distinct() -> None:
    assert V6_CONSUMER.is_file()
    assert V6_CONSUMER.read_bytes() != V7_SOURCE.read_bytes()
    assert b"CONTRACT_VERSION = 6" in V6_CONSUMER.read_bytes()
    assert b"CONTRACT_VERSION = 7" in V7_SOURCE.read_bytes()
