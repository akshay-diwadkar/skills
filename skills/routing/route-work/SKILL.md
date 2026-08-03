---
name: route-work
description: Route work requests across engineering, research, technical communication, and general workflows without executing them. Use when the user does not know which suite skill applies, asks which workflow to use, or gives an ambiguous request combining ideation, discovery, design, planning, implementation, audit, optimization, issue management, diagramming, or documentation that could trigger multiple heavyweight skills.
version: 3.1.0
metadata:
  invocation: model-invoked
disable-model-invocation: false
user-invocable: false
---

# Route Work

## Purpose

Classify one request and emit one routing decision with an ordered guidance
workflow and an inline `route_handoff` Markdown document with a Mermaid route
diagram; stop. Remain read-only.
Never plan, edit source, publish, commit, push, create a pull request, invoke a
selected skill, or create an input file for conversational text.

## Start

Resolve `skill-root`. Read [Routing Policy](references/routing-policy.md), then
run the stateless CLI with caller-known facts:

```bash
python <skill-root>/scripts/cli.py --repo-root <repo> --input request="<request>" --format json run
```

`result` carries the compact `route_handoff` inline; detailed guidance is opt-in
(`--handoff detailed`). Persist `route-handoff.md` only through the CLI
(`--output-file`, `--output-dir`, `handoff_output`) at a caller-chosen path
outside the repository. `--request-file` only for existing files. Pass
repository, approved-plan, or issue facts only when already known; the router
never inspects plan contents or contacts GitHub.

## Next-step loop

Run the router once, read the single decision from `result`, and do not invoke
a prerequisite, primary skill, or follow-up. Precedence: explicit skill names
and chains, then approved-plan execution, then implicit ideation, then
remaining evidence rules.

## Completion and recovery

Return the exact JSON object in `result` with no prose or follow-up execution.
Complete only when it holds exactly the routing-decision schema fields and the
target repository is unchanged. Invalid or missing inputs fail closed; correct
the caller-supplied fact and rerun once, never inferring missing authority or
continuing into the selected workflow.
