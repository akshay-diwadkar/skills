# Plan Change v7

`plan-change` adds narrow mechanical proof to native agent planning. The agent
explores the repository, writes one v7 draft, and runs one stateless command:

```bash
python scripts/cli.py --repo-root /absolute/repo \
  --input request_file=/absolute/request.md \
  --input draft_file=/absolute/plan.md --format json run
```

The result is the exact sealed Markdown. No run directory, classification,
baseline, inventory, scaffold, or second validation pass is created. Runtime
code opens only explicitly cited or targeted files and minimal Git identity
metadata; it does not claim to prove repository-wide completeness.

Plan-contract v7 requires obligation traceability, an explicit `CH` dependency
graph, and propagation accounting for shared changes. Downstream consumers keep
an isolated frozen v6 reader for historical sealed plans.

For the upstream architecture handoff, see [design-codebase](../design-codebase/README.md).
