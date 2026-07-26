from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "skills" / "engineering" / "plan-change" / "scripts"
sys.path.insert(0, str(SCRIPTS))
from plan_runtime import validate_plan  # noqa: E402

SPEC = importlib.util.spec_from_file_location("hardening_helpers", Path(__file__).with_name("hardening_helpers.py"))
assert SPEC and SPEC.loader
HELPERS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPERS)


def test_domain_specific_blueprints_aggregate_without_cross_domain_failures(tmp_path: Path) -> None:
    text = HELPERS.hydrated_scaffold(ROOT, tmp_path, "high-risk", ["security", "concurrency"])
    _plan, diagnostics = validate_plan(text, tmp_path)
    assert not [item for item in diagnostics if item.code.startswith("blueprint.")]


def test_blueprint_requires_every_concept_group(tmp_path: Path) -> None:
    text = HELPERS.hydrated_scaffold(ROOT, tmp_path, "high-risk", ["security"])
    text = text.replace("deny", "omit-concept")
    _plan, diagnostics = validate_plan(text, tmp_path)
    assert any(item.code == "blueprint.domain_concept" for item in diagnostics)
