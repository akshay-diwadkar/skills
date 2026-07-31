---
name: route-engineering-work
description: Route engineering requests to one repository workflow without executing it. Use when the user does not know which suite skill applies, asks which engineering workflow to use, combines discovery, design, planning, implementation, audit, optimization, issue, diagram, or manual work, or gives an ambiguous request that could trigger multiple heavyweight skills.
version: 1.3.0
metadata:
  invocation: model-invoked
disable-model-invocation: false
user-invocable: false
---

# Route Engineering Work

Classify the request, emit one routing decision, and stop. Never execute the
selected workflow.

Use the stateless common entrypoint when a protocol envelope is needed:

```bash
python scripts/cli.py --repo-root /absolute/repo \
  --input request="<request>" --format json run
```

It creates no run state and returns the router decision in `result`. The
existing `route_engineering_work.py` output remains the exact legacy JSON.

## Safety Boundary

Remain read-only. Never plan a change, edit source, publish an issue, commit,
push, create a pull request, or invoke a selected skill's runtime. Do not create
an input file for a conversational request.

## Route

1. Resolve `skill-root` as the directory containing this file.
2. Read [references/routing-policy.md](references/routing-policy.md).
3. Run the router once from `skill-root`:

   ```bash
   python scripts/route_engineering_work.py --request "<request>"
   ```

   Use `--request-file /absolute/path/to/request.txt` only when that file
   already exists. Add only facts already available to the caller:

   ```bash
   python scripts/route_engineering_work.py \
     --request "<request>" \
     --repo-root /absolute/path/to/repository \
     --approved-plan /absolute/path/to/approved-plan.md \
     --issue-number 42
   ```

4. Return the exact JSON object written to stdout. Do not add prose, invoke a
   prerequisite, invoke the primary skill, or begin a follow-up.

The router validates supplied paths but does not inspect an approved plan's
contents or contact GitHub. Omit facts that are not already known. Invalid
inputs fail closed without a routing decision.

## Completion

Complete only when stdout contains one JSON decision with exactly the fields
defined by `schemas/routing-decision.schema.json` and the target repository is
unchanged.
