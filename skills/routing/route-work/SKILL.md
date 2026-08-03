---
name: route-work
description: Classify a work request and return one routing decision with an inline `route_handoff` Mermaid guidance document without executing it. Use when no suite skill clearly applies.
version: 3.2.0
metadata:
  invocation: model-invoked
disable-model-invocation: false
user-invocable: false
---

# Route Work

## Purpose

Classify one request and emit one routing decision with an inline
`route_handoff` Mermaid document; stop. Remain read-only.
Never plan, edit source, publish, commit, push, create a pull request, invoke a
selected skill, or create an input file for conversational text.

## Start

Resolve `skill-root`. Read [Routing Policy](references/routing-policy.md), then
run the stateless common CLI with caller-known protocol inputs:

```bash
python <skill-root>/scripts/cli.py \
  --repo-root <repo> \
  --input request="<request>" \
  --input handoff_detail=detailed \
  --input handoff_output=<external-path>/route-handoff.md \
  --format json \
  run
```

`result` carries the compact `route_handoff`; detailed guidance is opt-in via
`handoff_detail`. Persist `route-handoff.md` only through `handoff_output`;
paths inside the repository or installed skill are rejected before any write.
Optional `approved_plan` and `issue_number` inputs carry caller-known facts;
the router never inspects plans or contacts GitHub.

### Direct script interface

The skill also ships `scripts/route_work.py` with direct-script
options: `--handoff`, `--output-file`, `--output-dir`, `--request-file`,
`--approved-plan`, `--issue-number`.

## Next-step loop

Run the router once and read the single decision from `result`; do not invoke
a prerequisite, primary skill, or follow-up. Precedence: explicit skills and
chains, then approved-plan execution, then ideation, then remaining evidence
rules.

## Completion and recovery

Return the exact JSON object in `result` with no prose or follow-up execution.
Complete only when it holds exactly the routing-decision schema fields and the
target repository is unchanged. Invalid inputs fail closed; correct the
caller-supplied fact and rerun once, never inferring missing authority or
continuing into the selected workflow.
