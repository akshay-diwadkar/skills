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

Contract v7 adds an `Obligations` section whose `RQ` records anchor every
obligation to verbatim request text, requires the `CH` dependency graph
(`depends_on`, locality, reversibility) with cycle and ordering validation, and
requires propagation accounting for shared and non-tiny changes. An offline
deterministic quality fixture suite scores golden and weak v7 plans without any
provider, model, or network access.

Plan-contract v6 generation is not distributed in this skill. Downstream
consumers retain an isolated frozen v6 compatibility reader in `implement-plan`
for old artifacts.

For the upstream architecture handoff, see [design-codebase](../design-codebase/README.md).
