from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = REPO_ROOT / "skills" / "engineering" / "plan-change" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from plan_runtime import repo_snapshot  # noqa: E402
from v4_model import validate  # noqa: E402


def _plan(root: Path) -> str:
    source = root / "src" / "names.py"
    source.parent.mkdir()
    source.write_text(
        "def normalize_name(raw: str | None) -> str:\n    return raw.strip() if raw else ''\n", encoding="utf-8"
    )
    lines = source.read_text(encoding="utf-8").splitlines()
    excerpt = "\n".join(lines[:2]).encode()
    metadata = {
        "provisional": {"intent": "bug-fix", "risk_domains": [], "tier": "tiny"},
        "final": {"intent": "bug-fix", "risk_domains": [], "tier": "tiny"},
    }
    return f"""# Normalize null names
<!-- plan-contract: 4 -->
<!-- plan-metadata: {json.dumps(metadata, separators=(",", ":"))} -->
<!-- plan-repository: {{}} -->

## Outcome and Scope
- SC-1: given: raw is None | when: normalize_name runs | then: it returns empty string | unchanged: string stripping stays stable
- In scope: null normalization.
- Unchanged: non-null behavior.

## Evidence Ledger
- F-1: path: `src/names.py` | lines: 1-2 | anchor: `normalize_name` | excerpt-sha256: `{hashlib.sha256(excerpt).hexdigest()}` | file-sha256: `{hashlib.sha256(source.read_bytes()).hexdigest()}` | observation: nullable input is guarded locally.

## Decisions
- D-1: selected: return empty string | evidence: F-1 | rejected: return None | drawback: callers require strings.

## Implementation Specification
- CH-1: path: `src/names.py` | anchor: `normalize_name` | status: existing | evidence: F-1 | change: preserve string stripping and return empty string for null input.

## Propagation Record
- P-1: path: `src/names.py` | surface: normalize_name caller | disposition: changed | owner: CH-1.

## Boundary Traces
- B-1: class: API request | path: F-1 | flow: caller -> normalize_name -> return -> response.

## Domain Obligations
- O-none: not-applicable | evidence: F-1.

## Traceability
| Criterion / constraint | Changes | Tests |
|---|---|---|
| SC-1 | CH-1 | T-1 |

## Verification
- T-1: given: None and " Ada " | expect: empty string and "Ada" | command: `pytest tests/test_names.py`.

## Risks, Assumptions, and Attack
- Assumptions: None.
- A-forgotten-propagation: repaired | evidence: P-1.
- A-boundary-input: repaired | evidence: T-1.
- A-literal-implementation: repaired | evidence: D-1.
"""


def test_v4_tiny_plan_is_repository_grounded(tmp_path: Path) -> None:
    text = _plan(tmp_path)
    assert validate(text, tmp_path, "tiny") == []


def test_v4_rejects_stale_evidence_and_old_contract(tmp_path: Path) -> None:
    text = _plan(tmp_path)
    (tmp_path / "src" / "names.py").write_text(
        "def normalize_name(raw: str | None) -> str:\n    return raw.strip()\n", encoding="utf-8"
    )
    assert any(item.code == "evidence.excerpt_hash" for item in validate(text, tmp_path, "tiny"))
    assert any(
        item.code == "contract.marker"
        for item in validate(text.replace("plan-contract: 4", "plan-contract: 3"), tmp_path, "tiny")
    )


def test_v4_detects_planner_mutation(tmp_path: Path) -> None:
    text = _plan(tmp_path)
    baseline = repo_snapshot(tmp_path)
    (tmp_path / "created-by-planner.txt").write_text("unsafe", encoding="utf-8")
    assert any(
        item.code == "planning.worktree_mutated"
        for item in validate(text, tmp_path, "tiny", require_finalized=True, baseline=baseline)
    )
