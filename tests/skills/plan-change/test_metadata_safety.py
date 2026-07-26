from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills" / "engineering" / "plan-change" / "scripts"))
from plan_runtime import validate_plan  # noqa: E402


def _plan(metadata: str) -> str:
    return "<!-- plan-contract: 5 -->\n<!-- plan-metadata: " + metadata + " -->\n"


def test_malformed_metadata_is_total(tmp_path: Path) -> None:
    cases = ["[]", '{"provisional":[],"final":{}}', '{"provisional":{},"final":"x"}', '{"provisional":{"intent":"bug-fix","tier":"critical","risk_domains":null},"final":{"intent":"bug-fix","tier":"tiny","risk_domains":{}}}']
    for metadata in cases:
        _plan_value, diagnostics = validate_plan(_plan(metadata), tmp_path)
        assert diagnostics
        assert any(item.code.startswith("metadata.") for item in diagnostics)


def test_diagnostics_are_stably_ordered(tmp_path: Path) -> None:
    text = _plan('{"provisional":[],"final":"invalid"}')
    _value, first = validate_plan(text, tmp_path)
    _value, second = validate_plan(text, tmp_path)
    assert [(item.line, item.code, item.message) for item in first] == [
        (item.line, item.code, item.message) for item in second
    ]


def test_python_signature_return_is_structurally_verified(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    source = "def normalize(raw: str) -> str:\n    return raw.strip()\n"
    path = tmp_path / "src" / "names.py"
    path.write_text(source, encoding="utf-8")
    excerpt = source
    plan = f'''<!-- plan-contract: 5 -->
<!-- plan-metadata: {{"provisional":{{"intent":"bug-fix","tier":"tiny","risk_domains":[]}},"final":{{"intent":"bug-fix","tier":"tiny","risk_domains":[]}}}} -->
## Outcome and Scope
- SC-1: given: blank name input | when: normalize is called | then: blank result is returned | unchanged: nonblank names retain trimming
## Evidence Ledger
    - F-1: kind: function-signature | path: src/names.py | lines: 1-2 | anchor: normalize | excerpt-sha256: {hashlib.sha256(excerpt.encode()).hexdigest()} | file-sha256: {hashlib.sha256(source.encode()).hexdigest()} | observation: local normalizer | parameters: raw | returns: int | async: false
## Decisions
- D-1: selected: preserve normalizer shape | evidence: F-1 | rejected: replace public function | drawback: callers would need migration
## Implementation Specification
- CH-1: path: src/names.py | anchor: normalize | status: existing | evidence: F-1 | change: return empty string for blank input
## Propagation Record
- P-1: owner: CH-1 | because: F-1 | surface: direct-caller | disposition: changed
## Boundary Traces
- B-1: class: API request | path: F-1 | flow: request -> normalize -> response
## Domain Obligations
## Traceability
| Criterion / constraint | Changes | Tests |
|---|---|---|
| SC-1 | CH-1 | T-1 |
## Verification
- T-1: given: blank name | when: normalize runs | then: empty result | command: python -m pytest
## Risks, Assumptions, and Attack
- A-forgotten-propagation: status: repaired | finding: direct caller is covered | evidence: F-1 | resolution: CH-1, T-1
- A-boundary-input: status: dismissed | finding: request boundary is unchanged | evidence: F-1 | resolution: F-1
- A-literal-implementation: status: repaired | finding: selected behavior has a test | evidence: F-1 | resolution: CH-1, T-1
'''
    _plan_value, diagnostics = validate_plan(plan, tmp_path)
    assert any(item.code == "fact.signature_returns" for item in diagnostics)
    wrong_range = plan.replace("lines: 1-2", "lines: 2-2")
    _plan_value, diagnostics = validate_plan(wrong_range, tmp_path)
    assert any(item.code == "fact.signature" for item in diagnostics)
