# Epic-aware issue selection to plan handoff

`scope-issue` selects and narrows exactly one ready child of an epic for one
user task — or returns an honest non-selection state — and seals exactly one
`issue-handoff.md`.

Work happens in two stages. The selection stage binds immutable task and epic
anchors from `scope_inputs.json`, classifies candidates from the fetched
snapshot, and records the selection or a non-selection status. The narrowing
stage grounds only the selected child with verified local evidence.

Only a `plan-ready` handoff is supplied to `plan-change` as `request_file`.
`needs-info`, `blocked`, `close-candidate`, `needs-decomposition`,
`no-ready-issue`, and `epic-complete` remain terminal local records.
Implementation, branches, pull requests, and GitHub updates belong to other
explicitly invoked workflows.

Single-issue mode: when the snapshot declares `metadata.mode: "single"`
(fetched with `--issue-number`), the epic is that one issue and the frontier
collapses to a single candidate; no override or exclusions apply.

See the alternative [design handoff](../design-codebase/README.md).
