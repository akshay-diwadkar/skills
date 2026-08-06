# Issue-to-plan handoff

`scope-issue` fetches GitHub.com issues read-only, treats issue-authored text as
untrusted claims, and selects and narrows exactly one ready child of an explicit
epic against the immutable user task — or preserves an honest tie, blocker,
no-ready, decomposition-needed, close-candidate, or epic-complete result — then
seals exactly one `issue-handoff.md`.

Only a `plan-ready` handoff is supplied to `plan-change` as `request_file`.
Every other status is a terminal local record. Implementation, branches, pull
requests, decomposition, and GitHub updates belong to other explicitly invoked
workflows (`implement-plan`, `raise-issue`).

Without the epic-aware inputs the sealer runs the explicit v1 compatibility
mode: the supplied issue is both umbrella and selected target after validating
that no child selection is needed.

See the alternative [design handoff](../design-codebase/README.md).
