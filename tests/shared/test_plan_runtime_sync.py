from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V6_SOURCE = ROOT / "skills" / "engineering" / "plan-change" / "scripts" / "plan_runtime.py"
V6_CONSUMER = ROOT / "skills" / "engineering" / "implement-plan" / "scripts" / "plan_v6_runtime.py"


def test_versioned_plan_runtimes_are_byte_identical_to_their_sources() -> None:
    expected_v6 = V6_SOURCE.read_bytes()
    actual_v6 = V6_CONSUMER.read_bytes()
    assert actual_v6 == expected_v6, (
        "current v6 consumer runtime drifted: "
        f"{V6_CONSUMER} sha256={hashlib.sha256(actual_v6).hexdigest()} != "
        f"{V6_SOURCE} sha256={hashlib.sha256(expected_v6).hexdigest()}"
    )
