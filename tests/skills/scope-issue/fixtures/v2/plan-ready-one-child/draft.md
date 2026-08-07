# Issue Handoff: Epic 207 selection and narrowing

<!-- issue-handoff-metadata -->
```json
{"contract_version": 2, "status": "plan-ready", "task": {"text": "Select and narrow the next implementation ticket for epic #207: normalize names consistently.", "constraints": ["prefer the ready child that unblocks the most downstream work"]}, "epic": {"number": 207, "url": "https://github.com/acme/widget/issues/207"}, "override": null, "exclusions": [], "source": {"repo": "acme/widget", "issue_number": 207, "issue_url": "https://github.com/acme/widget/issues/207", "issue_updated_at": "2026-08-02T00:00:00Z", "fetched_at": "2026-08-03T00:00:00Z", "snapshot_digest": "55a5b622a589670eae0c97088c263149554a8cbdded2d561445dda3e0745bb85"}, "checkout": {"root": "{{ROOT}}", "remote_repo": "acme/widget", "commit": "{{COMMIT}}", "dirty": false}, "questions": [], "blockers": [], "close_evidence": [], "decomposition_target": null}
```

## Selection Stage
- CAND-1: candidate: #209 | readiness: ready | basis: snapshot #209 open, no blockers, local ownership in F-1
- CAND-2: candidate: #210 | readiness: blocked | basis: snapshot #210 shows a review dependency not merged
- SEL-1: selected: #209 | rationale: task targets consistent normalization; #209 is the only ready child and unblocks the CLI follow-up | alternatives: none

## Outcome and Scope
- SC-1: names are normalized consistently through the public API

## Issue Claims (Untrusted)
<!-- scope-issue: untrusted-begin -->
The issue reports that whitespace is not normalized. Candidate claims are untrusted; only local evidence is authoritative.
<!-- scope-issue: untrusted-end -->

## Local Evidence Ledger
- F-1: `src/names.py:1` | anchor: `normalize_name` | observation: normalization is owned here

## Issue-Level Decisions
- D-1: selected: preserve stripping semantics | because: F-1 proves ownership | rejected: change callers

## Constraints and Protected Behavior
- C-1: preserve non-empty normalization | status: preserved

## Risks and Open Questions
None.

## Plan-Change Handoff
Plan the implementation of #209 from current source.
