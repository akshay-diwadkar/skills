from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCOPE_RUNTIME = ROOT / "skills" / "engineering" / "scope-issue" / "scripts" / "plan_runtime.py"
PLAN_RUNTIME = ROOT / "skills" / "engineering" / "plan-change" / "scripts" / "plan_runtime.py"


def test_shared_plan_runtime_is_byte_identical() -> None:
    scope_bytes = SCOPE_RUNTIME.read_bytes()
    plan_bytes = PLAN_RUNTIME.read_bytes()
    assert scope_bytes == plan_bytes, (
        "shared plan runtime drifted: "
        f"{SCOPE_RUNTIME} sha256={hashlib.sha256(scope_bytes).hexdigest()} != "
        f"{PLAN_RUNTIME} sha256={hashlib.sha256(plan_bytes).hexdigest()}"
    )
