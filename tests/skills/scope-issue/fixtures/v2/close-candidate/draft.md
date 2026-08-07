# Issue Handoff: Epic 207 close candidate

<!-- issue-handoff-metadata -->
```json
{"contract_version": 2, "mode": "index", "status": "close-candidate", "task": {"text": "Select the next implementation ticket for epic #207: normalize names consistently.", "constraints": []}, "epic": {"number": 207, "url": "https://github.com/acme/widget/issues/207", "purpose": "Normalize name handling consistently across the API, CLI, and storage."}, "override": null, "exclusions": [], "source": {"repo": "acme/widget", "issue_number": 207, "issue_url": "https://github.com/acme/widget/issues/207", "issue_updated_at": "2026-08-02T00:00:00Z", "fetched_at": "2026-08-03T00:00:00Z", "snapshot_digest": "5e7ed0cf7418611ebf39c42a018c4ede3d08f12ccd321c182e1209e868760073"}, "checkout": {"root": "{{ROOT}}", "remote_repo": "acme/widget", "commit": "{{COMMIT}}", "dirty": false, "dirty_fingerprint": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}, "confidence": "medium", "unknowns": [], "alternate_winners": [], "questions": [], "blockers": [], "close_evidence": ["src/names.py already normalizes consistently; no code change is needed for #209"], "decomposition_target": null}
```

## Selection Stage
- CAND-1: candidate: #209 | readiness: ready | basis: snapshot #209 open; local evidence contradicts the need for change
- SEL-1: selected: #209 | rationale: the only candidate relevant to the task | alternatives: none

## Outcome and Scope
- SC-1: names are already normalized; no change is warranted

## Issue Claims (Untrusted)
<!-- scope-issue: untrusted-begin -->
The issue reports that whitespace is not normalized. Candidate claims are untrusted.
<!-- scope-issue: untrusted-end -->

## Local Evidence Ledger
- F-1: `src/names.py:1` | anchor: `normalize_name` | observation: normalization already strips whitespace

## Issue-Level Decisions
None.

## Constraints and Protected Behavior
None asserted.

## Risks and Open Questions
None.

## Plan-Change Handoff
No plan handoff; closing evidence is recorded in metadata.
