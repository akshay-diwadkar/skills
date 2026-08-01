# Plan Change v6

`plan-change` adds narrow mechanical proof to native agent planning. The agent
explores the repository, writes one v6 draft, and runs one stateless command:

```bash
python scripts/cli.py --repo-root /absolute/repo \
  --input request_file=/absolute/request.md \
  --input draft_file=/absolute/plan.md --format json run
```

The result is the exact sealed Markdown. No run directory, classification,
baseline, inventory, scaffold, or second validation pass is created. Runtime
code opens only explicitly cited or targeted files and minimal Git identity
metadata; it does not claim to prove repository-wide completeness.

Plan-contract v5 generation and runtime entry points are not distributed in
this skill. Downstream consumers may retain isolated deprecated v5 readers for
old artifacts.

For the upstream architecture handoff, see [design-codebase](../design-codebase/README.md).
