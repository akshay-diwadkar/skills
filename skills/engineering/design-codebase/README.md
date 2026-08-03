# Design-to-plan handoff

`design-codebase` emits one validated `design-handoff.md`. Supply that exact file to
`plan-change` as `request_file`; the planning agent then explores the checkout,
writes a separate plan-contract v6 draft, and runs the stateless one-pass
sealer with both paths.

The design handoff is sealed in one command; validation, evidence-hash
backfill, typed receipt, and the atomic `design-handoff.md` write are not separate steps:

```bash
python /absolute/design-codebase/scripts/seal_assessment.py \
  --repo-root /absolute/repo --output-dir /absolute/design-output \
  --format json /absolute/design-draft.md
```

```bash
python /absolute/plan-change/scripts/cli.py --repo-root /absolute/repo \
  --input request_file=/absolute/design-output/design-handoff.md \
  --input draft_file=/absolute/plan.md --format json run
```

The handoff remains design evidence and intent, not a repository inventory or
an implementation plan. The v6 proof binds its request digest and only the
repository files cited by the agent-authored draft.

See [plan-change](../plan-change/README.md) and
[scope-issue](../scope-issue/README.md) for the two supported planning inputs.
