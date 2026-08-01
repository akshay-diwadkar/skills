# Scope Issue

`scope-issue` is the GitHub issue entry point to the proof-carrying planning
pipeline. It fetches GitHub.com issues with `gh`, treats issue-authored text as
untrusted claims, and grounds one selected issue against a local checkout.

## Handoff contract

Pass the validated issue artifact to `plan-change` as `request_file`, explore
the checkout natively, author one v6 draft, and seal it with the stateless run
command. Preserve these source markers beneath the plan markers:

- `source-issue-plan-sha256`
- `source-base-commit`
- `source-issue-updated-at`

Senior handoff validation accepts plan-contract v6 and deprecated finalized v5
plans for one release. V6 validation uses the supplied plan-change runtime;
isolated v5 parsing exists only for old downstream artifacts and is not part of
the plan-change distribution.

See the [design-to-plan pipeline](../design-codebase/README.md) for the
alternative design handoff.
