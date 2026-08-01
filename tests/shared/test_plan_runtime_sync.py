from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V5_SOURCE = ROOT / "tools" / "plan_contract_runtime.py"
V5_CONSUMERS = (
    ROOT / "skills" / "engineering" / "scope-issue" / "scripts" / "plan_runtime.py",
    ROOT / "skills" / "engineering" / "implement-plan" / "scripts" / "plan_runtime.py",
)
V6_SOURCE = ROOT / "skills" / "engineering" / "plan-change" / "scripts" / "plan_runtime.py"
V6_CONSUMER = ROOT / "skills" / "engineering" / "implement-plan" / "scripts" / "plan_v6_runtime.py"


def test_versioned_plan_runtimes_are_byte_identical_to_their_sources() -> None:
    expected_v5 = V5_SOURCE.read_bytes()
    for consumer in V5_CONSUMERS:
        actual = consumer.read_bytes()
        assert actual == expected_v5, (
            "deprecated v5 consumer runtime drifted: "
            f"{consumer} sha256={hashlib.sha256(actual).hexdigest()} != "
            f"{V5_SOURCE} sha256={hashlib.sha256(expected_v5).hexdigest()}"
        )
    expected_v6 = V6_SOURCE.read_bytes()
    actual_v6 = V6_CONSUMER.read_bytes()
    assert actual_v6 == expected_v6, (
        "current v6 consumer runtime drifted: "
        f"{V6_CONSUMER} sha256={hashlib.sha256(actual_v6).hexdigest()} != "
        f"{V6_SOURCE} sha256={hashlib.sha256(expected_v6).hexdigest()}"
    )
