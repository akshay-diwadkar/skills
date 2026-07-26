from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills" / "engineering" / "plan-change" / "scripts"))
from plan_runtime import finalized_text, validate_plan  # noqa: E402


def draft(repo: Path, *, tier: str = "tiny") -> str:
    path = repo / "src" / "names.py"
    content = path.read_bytes()
    excerpt = b"def normalize_name(raw: str) -> str:\n"
    body = f'''# Normalize name
<!-- plan-contract: 5 -->
<!-- plan-metadata: {{"provisional":{{"intent":"bug-fix","risk_domains":[],"tier":"{tier}"}},"final":{{"intent":"bug-fix","risk_domains":[],"tier":"{tier}"}}}} -->

## Outcome and Scope
- SC-1: given: blank input | when: normalize_name runs | then: stable normalized output | unchanged: nonblank normalization remains stable
## Evidence Ledger
- F-1: kind: function-signature | path: src/names.py | lines: 1-1 | anchor: normalize_name | excerpt-sha256: {hashlib.sha256(excerpt).hexdigest()} | file-sha256: {hashlib.sha256(content).hexdigest()} | observation: planner-authored observation | parameters: raw: str | returns: str
## Decisions
- D-1: selected: preserve local behavior | evidence: F-1 | rejected: rewrite interface | drawback: changes the existing local contract
## Implementation Specification
- CH-1: path: src/names.py | anchor: normalize_name | status: existing | evidence: F-1 | change: handle blank input before normalization
## Propagation Record
- P-1: owner: CH-1 | because: F-1 | surface: direct-caller | disposition: unchanged
## Boundary Traces
- B-1: class: API request | path: F-1 | flow: request -> normalize_name -> result
## Domain Obligations
## Traceability
| Criterion / constraint | Changes | Tests |
|---|---|---|
| SC-1 | CH-1 | T-1 |
## Verification
- T-1: given: blank input | when: normalize_name runs | then: stable result | command: python -m pytest
## Risks, Assumptions, and Attack
- A-forgotten-propagation: status: repaired | finding: propagation inventory reviewed | evidence: F-1 | resolution: CH-1, T-1
- A-boundary-input: status: dismissed | finding: unchanged boundary | evidence: F-1 | resolution: F-1
- A-literal-implementation: status: repaired | finding: decision is explicit | evidence: F-1 | resolution: CH-1, T-1
'''
    return body


def test_v5_finalization_and_targeted_binding(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "names.py").write_text("def normalize_name(raw: str) -> str:\n    return raw.strip()\n")
    finalized = finalized_text(draft(tmp_path), tmp_path)
    _, diagnostics = validate_plan(finalized, tmp_path, require_finalized=True)
    assert diagnostics == []
    (tmp_path / "unrelated.txt").write_text("allowed")
    _, diagnostics = validate_plan(finalized, tmp_path, require_finalized=True)
    assert diagnostics == []
    (tmp_path / "src" / "names.py").write_text("changed\n")
    _, diagnostics = validate_plan(finalized, tmp_path, require_finalized=True)
    assert any(item.code in {"fact.stale", "binding.stale"} for item in diagnostics)


def test_unsupported_contract_is_single_diagnostic(tmp_path: Path) -> None:
    _, diagnostics = validate_plan("<!-- plan-contract: 4 -->\n", tmp_path)
    assert [item.code for item in diagnostics] == ["contract.unsupported"]


def test_generated_runtimes_are_exact_copies() -> None:
    source = (ROOT / "tools" / "plan_contract_runtime.py").read_text(encoding="utf-8")
    for skill in ("plan-change", "implement-plan", "scope-issue"):
        assert (ROOT / "skills" / "engineering" / skill / "scripts" / "plan_runtime.py").read_text(
            encoding="utf-8"
        ) == source


def test_required_records_and_typed_references_fail_closed(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "names.py").write_text("def normalize_name(raw: str) -> str:\n    return raw.strip()\n")
    text = draft(tmp_path).replace("## Boundary Traces\n- B-1: class: API request | path: F-1 | flow: request -> normalize_name -> result\n", "## Boundary Traces\n")
    text = text.replace("evidence: F-1 | rejected", "evidence: T-1 | rejected")
    _, diagnostics = validate_plan(text, tmp_path)
    assert {item.code for item in diagnostics} >= {"record.required", "reference.type"}


def test_same_path_wrong_anchor_and_new_target_are_rejected(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "names.py").write_text("def normalize_name(raw: str) -> str:\n    return raw.strip()\n")
    text = draft(tmp_path).replace("anchor: normalize_name | status: existing", "anchor: other_name | status: existing")
    _, diagnostics = validate_plan(text, tmp_path)
    assert any(item.code == "change.evidence_anchor" for item in diagnostics)
    text = draft(tmp_path).replace("status: existing", "status: new").replace("path: src/names.py", "path: ../escape.py")
    _, diagnostics = validate_plan(text, tmp_path)
    assert any(item.code == "change.new_path" for item in diagnostics)


def test_unknown_and_duplicate_attacks_are_rejected(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "names.py").write_text("def normalize_name(raw: str) -> str:\n    return raw.strip()\n")
    text = draft(tmp_path) + "- A-invented: status: dismissed | finding: invented attack reviewed | evidence: F-1 | resolution: F-1\n- A-boundary-input: status: dismissed | finding: duplicate boundary review | evidence: F-1 | resolution: F-1\n"
    _plan, diagnostics = validate_plan(text, tmp_path)
    assert {item.code for item in diagnostics} >= {"attack.unknown", "attack.duplicate"}


def test_baseline_detects_planner_mutation_but_binding_allows_unrelated_change(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    target = tmp_path / "src" / "names.py"
    target.write_text("def normalize_name(raw: str) -> str:\n    return raw.strip()\n")
    from plan_runtime import snapshot  # noqa: E402

    baseline = snapshot(tmp_path)
    target.write_text("changed\n")
    _, diagnostics = validate_plan(draft(tmp_path), tmp_path, baseline=baseline)
    assert any(item.code == "snapshot.mutation" for item in diagnostics)


def test_every_scaffold_places_blueprints_inside_implementation_specification() -> None:
    import importlib.util

    path = ROOT / "skills" / "engineering" / "plan-change" / "scripts" / "plan_contract.py"
    spec = importlib.util.spec_from_file_location("plan_scaffold_contract", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for tier in ("tiny", "standard", "high-risk"):
        plan, diagnostics = module.render_scaffold(tier, "bug-fix", []) and __import__("plan_runtime").parse_plan(module.render_scaffold(tier, "bug-fix", []))
        assert plan is not None
        assert not [item for item in diagnostics if item.code == "blueprint.location"]
