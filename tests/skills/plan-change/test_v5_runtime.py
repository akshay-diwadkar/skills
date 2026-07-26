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
- F-1: kind: function-signature | path: src/names.py | lines: 1-1 | anchor: normalize_name | excerpt-sha256: {hashlib.sha256(excerpt).hexdigest()} | file-sha256: {hashlib.sha256(content).hexdigest()} | observation: planner-authored observation
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
