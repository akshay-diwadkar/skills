"""Create finalized, repository-bound v4 plans for cross-skill tests."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "engineering" / "plan-change" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from plan_runtime import finalized_text, repo_snapshot  # noqa: E402
from v4_model import binding_for  # noqa: E402


def finalized_tiny_plan(repo: Path, path: str = "src/names.py", anchor: str = "normalize_name") -> str:
    source = repo / path
    lines = source.read_text(encoding="utf-8").splitlines()
    excerpt = "\n".join(lines).encode("utf-8")
    metadata = {
        "provisional": {"intent": "bug-fix", "risk_domains": [], "tier": "tiny"},
        "final": {"intent": "bug-fix", "risk_domains": [], "tier": "tiny"},
    }
    draft = f'''# Normalize names safely
<!-- plan-contract: 4 -->
<!-- plan-metadata: {json.dumps(metadata, separators=(",", ":"))} -->
<!-- plan-repository: {{}} -->

## Outcome and Scope
- SC-1: given: a missing name | when: {anchor} runs | then: it returns an empty string | unchanged: valid strings preserve normalization
- In scope: `{path}` null handling.
- Unchanged: existing string behavior.

## Evidence Ledger
- F-1: path: `{path}` | lines: 1-{len(lines)} | anchor: `{anchor}` | excerpt-sha256: `{hashlib.sha256(excerpt).hexdigest()}` | file-sha256: `{hashlib.sha256(source.read_bytes()).hexdigest()}` | observation: normalization is owned by the named function.

## Decisions
- D-1: selected: guard missing input locally | evidence: F-1 | rejected: widen the return contract | drawback: callers require strings.

## Implementation Specification
- CH-1: path: `{path}` | anchor: `{anchor}` | status: existing | evidence: F-1 | change: return an empty string for missing input and preserve valid-string behavior.

## Propagation Record
- P-1: path: `{path}` | surface: {anchor} caller | disposition: changed | owner: CH-1.

## Boundary Traces
- B-1: class: API request | path: F-1 | flow: caller -> {anchor} -> return -> response.

## Domain Obligations
- O-none: not-applicable | evidence: F-1.

## Traceability
| Criterion / constraint | Changes | Tests |
|---|---|---|
| SC-1 | CH-1 | T-1 |

## Verification
- T-1: given: missing and padded names | expect: empty and normalized strings | command: `python -m pytest -q`.

## Risks, Assumptions, and Attack
- Assumptions: None.
- A-forgotten-propagation: repaired | evidence: P-1.
- A-boundary-input: repaired | evidence: T-1.
- A-literal-implementation: repaired | evidence: D-1.
'''
    binding = binding_for(draft, repo)
    bound = draft.replace("<!-- plan-repository: {} -->", "<!-- plan-repository: " + json.dumps(binding, sort_keys=True, separators=(",", ":")) + " -->")
    return finalized_text(bound, binding)


def planning_snapshot(repo: Path) -> dict:
    """Expose an in-memory snapshot for no-mutation assertions."""
    return repo_snapshot(repo)
