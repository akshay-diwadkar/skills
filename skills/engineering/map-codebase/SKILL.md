---
name: map-codebase
description: Map unfamiliar or large repositories into compact machine knowledge and resolve implementation ownership before editing. Use for codebase orientation or structure questions, "where is X implemented?" or "which file handles Y?" navigation, pre-change ownership checks, refreshing knowledge after changes, or setting up AGENTS.md/CLAUDE.md references and scheduled refresh workflows.
version: 2.4.2
metadata:
  invocation: model-invoked
disable-model-invocation: false
user-invocable: false
---

# Map Codebase

## Purpose and authority

Use compact repository knowledge to locate ownership, constraints, and impacts;
verify every conclusion in current source. Never preload maps or all symbol
shards. Medium confidence is not verified ownership, and missing or stale
knowledge never blocks direct source inspection.

Implicit invocation is read-only. Do not build, refresh, record analytics,
modify repository knowledge guidance, or generate workflows without explicit write authority.

## Start

Resolve `skill-root` to this directory and choose an external run directory:

```bash
python /absolute/skill-root/scripts/cli.py --repo-root /absolute/repo \
  --run-dir /absolute/run --input task="locate authentication ownership" \
  --format json doctor
```

Run the returned `next_command.argv` with its returned `cwd`. Read only
`required_reads`, verify their named source targets, and stop on every
`blocking_reason`.

## Next-step loop

1. Resolve ownership first; stop when the owner and source contract are verified.
2. Run `next` only when the response names an unresolved constraint trigger.
3. Expand to impacts only when the constraints response names an impact trigger.
4. After an authorized coherent change set, refresh and validate knowledge.

Use [Knowledge Contract](references/knowledge-contract.md) for freshness,
scope, write authority, agent-document, and workflow rules. Use
[Resolver Design](references/resolver-design.md) only for ranking or phase
diagnosis, [Worked Resolver Walkthrough](references/example-walkthrough.md) for
partial-staleness recovery, and [Extractor Coverage](references/extractor-coverage.md)
for language support. Do not use `--phase all` except for explicit debugging or
human inspection.

## Completion and recovery

Complete when the requested phase stop condition is met in current source; a
phase `complete` response additionally supplies verified impact candidates.

For missing, invalid, or stale knowledge, follow the status recommendation and
build or refresh only with write authority. On resolver failure, use its bounded
fallback searches and inspect source directly. Never treat generated knowledge
as more authoritative than the repository.
