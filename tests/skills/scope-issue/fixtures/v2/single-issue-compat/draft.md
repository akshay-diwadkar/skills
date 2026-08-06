# Issue Handoff: Normalize names

<!-- issue-handoff-metadata -->
```json
{"contract_version": 2, "status": "plan-ready", "task": {"text": "Work issue #7: normalize names consistently.", "constraints": []}, "epic": {"number": 7, "url": "https://github.com/acme/widget/issues/7"}, "override": null, "exclusions": [], "source": {"repo": "acme/widget", "issue_number": 7, "issue_url": "https://github.com/acme/widget/issues/7", "issue_updated_at": "2026-08-02T00:00:00Z", "fetched_at": "2026-08-03T00:00:00Z"}, "checkout": {"root": "{{ROOT}}", "remote_repo": "acme/widget", "commit": "{{COMMIT}}", "dirty": false}, "questions": [], "blockers": [], "close_evidence": []}
```

## Selection Stage
- CAND-1: candidate: #7 | readiness: ready | basis: snapshot #7 single-issue; no children require selection
- SEL-1: selected: #7 | rationale: the user's task names issue #7 directly | alternatives: none

## Outcome and Scope
- SC-1: names are normalized consistently

## Issue Claims (Untrusted)
Reporter says whitespace fails.

## Local Evidence Ledger
- F-1: `src/names.py:1` | anchor: `normalize_name` | observation: normalization is owned here

## Issue-Level Decisions
- D-1: selected: preserve stripping | because: F-1 proves ownership | rejected: change callers

## Constraints and Protected Behavior
- C-1: preserve non-empty normalization | status: preserved

## Risks and Open Questions
None.

## Plan-Change Handoff
Plan the implementation from current source.
