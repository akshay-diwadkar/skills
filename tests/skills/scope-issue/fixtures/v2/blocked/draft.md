# Issue Handoff: Epic 207 blocked during narrowing

<!-- issue-handoff-metadata -->
```json
{"contract_version": 2, "status": "blocked", "task": {"text": "Select the next implementation ticket for epic #207: normalize names consistently.", "constraints": []}, "epic": {"number": 207, "url": "https://github.com/acme/widget/issues/207"}, "override": null, "exclusions": [], "source": {"repo": "acme/widget", "issue_number": 207, "issue_url": "https://github.com/acme/widget/issues/207", "issue_updated_at": "2026-08-02T00:00:00Z", "fetched_at": "2026-08-03T00:00:00Z", "snapshot_digest": "5e7ed0cf7418611ebf39c42a018c4ede3d08f12ccd321c182e1209e868760073"}, "checkout": {"root": "{{ROOT}}", "remote_repo": "acme/widget", "commit": "{{COMMIT}}", "dirty": false}, "questions": [], "blockers": ["GitHub API credentials are unavailable; linked PR state for #209 cannot be fetched"], "close_evidence": [], "decomposition_target": null}
```

## Selection Stage
- CAND-1: candidate: #209 | readiness: ready | basis: snapshot #209 open; PR state unverified
- SEL-1: selected: #209 | rationale: only ready child matching the task | alternatives: none

## Outcome and Scope
- SC-1: names are normalized consistently through the public API

## Issue Claims (Untrusted)
<!-- scope-issue: untrusted-begin -->
The issue reports that whitespace is not normalized. Candidate claims are untrusted.
<!-- scope-issue: untrusted-end -->

## Local Evidence Ledger
- F-1: `src/names.py:1` | anchor: `normalize_name` | observation: normalization is owned here

## Issue-Level Decisions
None.

## Constraints and Protected Behavior
None asserted.

## Risks and Open Questions
None.

## Plan-Change Handoff
No plan handoff while blocked; unblock conditions are recorded in metadata.
