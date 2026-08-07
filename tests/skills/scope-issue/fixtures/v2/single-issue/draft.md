# Issue Handoff: Normalize names

<!-- issue-handoff-metadata -->
```json
{"contract_version": 2, "mode": "single", "status": "plan-ready", "task": {"text": "Work issue #7: normalize names consistently.", "constraints": []}, "epic": {"number": 7, "url": "https://github.com/acme/widget/issues/7", "purpose": "Normalize names consistently in the public API."}, "override": null, "exclusions": [], "source": {"repo": "acme/widget", "issue_number": 7, "issue_url": "https://github.com/acme/widget/issues/7", "issue_updated_at": "2026-08-02T00:00:00Z", "fetched_at": "2026-08-03T00:00:00Z", "snapshot_digest": "585e92e113802eef503cad6e02c67e517b17164dabd9f6826f4500aaf94162d7"}, "checkout": {"root": "{{ROOT}}", "remote_repo": "acme/widget", "commit": "{{COMMIT}}", "dirty": false, "dirty_fingerprint": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}, "confidence": "high", "unknowns": [], "alternate_winners": [], "questions": [], "blockers": [], "close_evidence": [], "decomposition_target": null}
```

## Selection Stage
- CAND-1: candidate: #7 | readiness: ready | basis: snapshot #7 single-issue; no children require selection
- SEL-1: selected: #7 | rationale: the user's task names issue #7 directly | alternatives: none

## Outcome and Scope
- SC-1: names are normalized consistently

## Issue Claims (Untrusted)
<!-- scope-issue: untrusted-begin -->
Reporter says whitespace fails.
<!-- scope-issue: untrusted-end -->

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
