---
name: route-work
description: Validate the agent-chosen workflow across suite skills and return one inline `route_handoff` decision. Use when no suite skill clearly applies and the agent must confirm its selection.
version: 4.0.1
metadata:
  invocation: model-invoked
disable-model-invocation: false
user-invocable: false
---

# Route Work

## Purpose

Validate the agent-selected workflow and emit one `route_handoff` Mermaid
routing decision; stop. Remain read-only.
Never plan, edit source, publish, commit, push, create a PR, invoke a selected
skill, or create conversational input files.

## Start

The agent owns every routing choice; the router only validates it. Read
[Routing Policy](references/routing-policy.md), then run the stateless common
CLI:

```bash
python <skill-root>/scripts/cli.py --repo-root <repo> \
  --input selected_skills=<skill> --input primary_skill=<primary> \
  --format json run
```

Repeat `selected_skills`, `excluded_skills`, `required_capabilities` once per
value; add `rationale`/`intent` to echo. Facts are declared `=true` only when
known true: `audit_handoff_available`, `approved_plan_available`,
`issue_context_available`, `repository_navigation_inadequate`.
`handoff_detail=detailed` opts into detailed guidance; `handoff_output`
persists `route-handoff.md` outside the repository and installed skill
(rejected otherwise, including symlinked paths).

### Direct script interface

`scripts/route_work.py` accepts the same inputs as CLI flags
(`--selected-skill`, `--primary-skill`, per-fact flags, `--handoff`,
`--output-file`, `--output-dir`); see `--help` for the full list.

## Next-step loop

Run the router once: `valid: true` means the workflow (reordered when needed)
is ready; otherwise correct the selection against the Routing Policy error
codes and rerun once. Never repair an error by inference.

## Completion and recovery

Return the exact JSON object in `result` with no prose or follow-up execution.
Complete only when it holds the route-validation schema fields and the
repository is unchanged. Invalid selections fail closed: correct the selection
and rerun once, never inferring authority or executing the workflow.
