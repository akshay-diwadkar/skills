# Issue Handoff: Epic 207 needs decomposition

<!-- issue-handoff-metadata -->
```json
{"contract_version": 2, "mode": "index", "status": "needs-decomposition", "task": {"text": "Select the next implementation ticket for epic #207: normalize names consistently.", "constraints": []}, "epic": {"number": 207, "url": "https://github.com/acme/widget/issues/207", "purpose": "Normalize name handling consistently across the API, CLI, and storage."}, "override": null, "exclusions": [], "source": {"repo": "acme/widget", "issue_number": 207, "issue_url": "https://github.com/acme/widget/issues/207", "issue_updated_at": "2026-08-02T00:00:00Z", "fetched_at": "2026-08-03T00:00:00Z", "snapshot_digest": "d2025dbccc1d5e84311ef37dda7f75d4ef290ff6f08fd77e5d96332feb904693"}, "checkout": {"root": "{{ROOT}}", "remote_repo": "acme/widget", "commit": "{{COMMIT}}", "dirty": false, "dirty_fingerprint": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}, "confidence": "high", "unknowns": [], "questions": [], "blockers": [], "close_evidence": [], "decomposition_target": "CAND-1"}
```

## Selection Stage
- CAND-1: candidate: #209 | readiness: needs-decomposition | basis: snapshot #209 spans API, CLI, and storage layers; not one safely plannable unit
- No selection: the candidate must return to raise-issue for decomposition.

## Outcome and Scope
No child was selected or narrowed.

## Issue Claims (Untrusted)
<!-- scope-issue: untrusted-begin -->
Candidate claims are untrusted; only snapshot state was consulted.
<!-- scope-issue: untrusted-end -->

## Local Evidence Ledger
No local narrowing evidence was required.

## Issue-Level Decisions
None.

## Constraints and Protected Behavior
None asserted.

## Risks and Open Questions
None.

## Plan-Change Handoff
No plan handoff; #209 returns to raise-issue.
