# Issue-to-plan handoff

`scope-issue` fetches GitHub.com issues read-only, treats issue-authored text as
untrusted claims, grounds one selected issue locally, and seals exactly one
`issue-handoff.md`.

Only a `plan-ready` handoff is supplied to `plan-change` as `request_file`.
`needs-info`, `blocked`, and `close-candidate` remain terminal local records.
Implementation, branches, pull requests, and GitHub updates belong to other
explicitly invoked workflows.

See the alternative [design handoff](../design-codebase/README.md).
