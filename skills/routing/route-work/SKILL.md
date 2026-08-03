---
name: route-work
description: Route work requests across engineering, research, technical communication, and general workflows without executing them. Use when the user does not know which suite skill applies, asks which workflow to use, combines ideation, research, discovery, design, planning, implementation, audit, optimization, issue management, diagramming, or documentation, or gives an ambiguous request that could trigger multiple heavyweight skills.
version: 3.0.0
metadata:
  invocation: model-invoked
disable-model-invocation: false
user-invocable: false
---

# Route Work

## Purpose and authority

Classify one request, emit one routing decision with an ordered guidance workflow of skill steps and a sealed `route-handoff.md` artifact (including a Mermaid route diagram with decision branches and verification loops), and stop. Remain read-only.
Never plan, edit source, publish, commit, push, create a pull request, invoke a
selected skill, or create an input file for conversational text.

## Start

Resolve `skill-root` to this directory. Read [Routing Policy](references/routing-policy.md),
then run the stateless CLI with facts already available to the caller:

```bash
python /absolute/skill-root/scripts/cli.py --repo-root /absolute/repo \
  --input request="<request>" --format json run
```

Use `--request-file` only when that file already exists. Supply repository,
approved-plan, or issue facts only when already known; the router validates
paths but does not inspect plan contents or contact GitHub.

## Next-step loop

1. Run the router once from `skill-root`.
2. Read the single decision from `result`.
3. Do not invoke a prerequisite, primary skill, or follow-up.
4. Preserve the exact allowed and forbidden actions in the decision.

The direct `scripts/route_work.py` command remains the legacy JSON
entry point; use the common CLI when a protocol envelope is required.

## Completion and recovery

Return the exact JSON object in `result` with no prose or follow-up execution.
Complete only when it contains exactly the routing-decision schema fields and
the target repository is unchanged.

Invalid or missing inputs fail closed without a routing decision. Correct the
caller-supplied fact and rerun once; never infer missing authority or continue
into the selected workflow.
