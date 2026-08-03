from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from tools.diagnostics import (
    CATEGORIES,
    REQUIRED_FIELDS,
    Diagnostic,
    canonical_json,
    command,
    is_canonical,
    normalize_diagnostic,
    sorted_diagnostics,
)

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "tools" / "diagnostics" / "diagnostic.schema.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("category", CATEGORIES)
def test_every_category_produces_a_complete_repair(category: str) -> None:
    item = Diagnostic(
        code=f"example.{category}",
        message=f"Local failure for {category}.",
        category=category,
        skill="fixture-skill",
        phase="validate",
        artifact="fixture",
        record="F-1",
        field="sha256",
        path="fixture/input.json",
        supporting_evidence=("F-1.sha256 does not match fixture/input.json.",),
        next_command=command(["python", "check.py", "fixture/input.json"], ROOT),
        extensions={"hint": "Repair F-1.sha256.", "details": {}},
    ).to_dict()
    assert set(REQUIRED_FIELDS) <= set(item)
    assert is_canonical(item)
    assert item["valid_repairs"]
    assert item["supporting_evidence"]
    jsonschema.Draft202012Validator(SCHEMA).validate(item)


def test_normalization_preserves_aliases_and_is_byte_deterministic() -> None:
    legacy = {
        "code": "fact.stale",
        "message": "F-1 hash is stale for src/example.py.",
        "hint": "Refresh F-1 from src/example.py.",
        "details": {"line": 12},
        "line": 12,
    }
    first = normalize_diagnostic(
        legacy,
        skill="plan-change",
        phase="validate",
        artifact="plan",
        path="draft.md",
    )
    second = normalize_diagnostic(
        legacy,
        skill="plan-change",
        phase="validate",
        artifact="plan",
        path="draft.md",
    )
    assert first["record"] == "F-1"
    assert first["path"] == "src/example.py"
    assert first["hint"] == legacy["hint"]
    assert first["details"] == legacy["details"]
    assert canonical_json(first) == canonical_json(second)


def test_repairs_are_unique_and_evidence_and_diagnostics_are_sorted() -> None:
    item = Diagnostic(
        code="example.missing",
        message="T-1 evidence is missing.",
        category="missing_evidence",
        valid_repairs=("Add T-1 evidence.", "Add T-1 evidence."),
        supporting_evidence=("z", "a", "z"),
    ).to_dict()
    assert item["valid_repairs"] == ["Add T-1 evidence."]
    assert item["supporting_evidence"] == ["a", "z"]
    assert [entry["code"] for entry in sorted_diagnostics([{**item, "code": "z"}, {**item, "code": "a"}])] == [
        "a",
        "z",
    ]


def test_repair_text_never_weakens_validation() -> None:
    banned = ("bypass", "suppress", "downgrade", "weaken", "ignore the validation")
    source = (ROOT / "tools" / "diagnostics" / "runtime.py").read_text(encoding="utf-8").casefold()
    for phrase in banned:
        assert phrase not in source


def test_every_blocking_manifest_step_requests_structured_diagnostics() -> None:
    blocked = 0
    for manifest_path in sorted((ROOT / "skills").glob("*/*/skill-protocol.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for value in manifest["commands"].values():
            variants = value if isinstance(value, list) else [value]
            for variant in variants:
                for step in variant["steps"]:
                    if step["failure"] == "blocked":
                        blocked += 1
                        assert step["diagnostics_json"] is True, manifest_path
    # Stateless v4 sealers have one blocking command per normal-success path.
    assert blocked == 22
