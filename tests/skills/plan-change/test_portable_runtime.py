from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_portable_runtimes_have_identical_public_receipt_behavior(tmp_path: Path) -> None:
    planner = _load("planner_runtime", ROOT / "skills/engineering/plan-change/scripts/plan_runtime.py")
    implementer = _load("implementer_runtime", ROOT / "skills/engineering/implement-plan/scripts/plan_runtime.py")
    text = "# plan\n<!-- plan-contract: 4 -->\n"
    binding = {"repository_id": "example", "git_head": None, "dirty": False}
    assert planner.plan_digest(text) == implementer.plan_digest(text)
    assert planner.binding_digest(binding) == implementer.binding_digest(binding)
    assert planner.receipt_line(text, binding) == implementer.receipt_line(text, binding)
