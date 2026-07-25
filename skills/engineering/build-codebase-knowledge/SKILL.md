---
name: build-codebase-knowledge
description: Build and maintain a compact, deterministic repository-intelligence layer and task resolver to minimize broad repository scans, unnecessary file reads, context-window usage, and stale architectural assumptions. Use when navigating a complex codebase, starting a new task, resolving relevant files, or updating repository knowledge after code changes.
---

# Build Codebase Knowledge

Use committed repository knowledge as a navigation aid; source remains authoritative.

1. Run `python scripts/cli.py status --repo-root <repo>`.
2. Build only when artifacts are missing, stale, or schema-invalid.
3. Run `python scripts/cli.py resolve "<task>" --repo-root <repo> --format json` before broad searches.
4. Read only phase 1 first. Advance a phase only when its stop condition is not met.
5. Verify all behavioral claims in source before planning or editing.
6. After one coherent change set, run `refresh` with every changed path, then `validate`. Do not refresh after each edit.

Prefer resolver line/symbol slices and targeted `rg` fallbacks over opening entire files. Never treat a fresh index as proof of runtime behavior, and never regenerate an already-fresh index without a reason.

## Skill Directory Resolution

Execute runtime scripts with process `cwd` set to the active skill directory (containing this `SKILL.md`) or pass absolute paths:
- `skill-root`: absolute path to `skills/engineering/build-codebase-knowledge/`
- `repo-root`: absolute target repository path

## Workflow

### 1. Artifact Generation
When artifacts are missing or stale, build initial knowledge:
```bash
python scripts/build_knowledge.py --repo-root /absolute/path/to/repo
```
Outputs in `.agent/knowledge/`:
- `context.md`: High-density orientation (stack, entry points, commands, boundaries). Target <= 120 lines.
- `architecture.md`: Component matrix, dependency rules, runtime flow, risk points. Target <= 220 lines.
- `repo-map.json`: Schema-validated compact map of subsystems, files, entry points, commands, and configuration.
- `symbols.json` plus `symbols/*.json`: Shard catalog and on-demand symbol definitions.
- `relationships.json`: Imports, tests, configuration links, and unresolved edges.
- `manifest.json`: Revision, dirty/untracked state, inventory, hashes, and freshness state.

Also links knowledge docs in `AGENTS.md` and/or `CLAUDE.md` (or creates them if missing):
```bash
python scripts/link_agent_docs.py --repo-root /absolute/path/to/repo
# or via CLI:
python scripts/cli.py link-docs --repo-root /absolute/path/to/repo
```

To scaffold a GitHub Action workflow that automatically refreshes knowledge docs on push to main:
```bash
python scripts/scaffold_github_workflow.py --repo-root /absolute/path/to/repo --branch main
# or via CLI:
python scripts/cli.py generate-workflow --repo-root /absolute/path/to/repo --branch main
```

### 2. Task Resolution Pipeline
When assigned an engineering task, query the resolver:
```bash
python scripts/resolve_task.py --repo-root /absolute/path/to/repo --task "Add rate limiting to password reset" --format human
```
The resolver executes 7 deterministic pipeline stages:
- **Stage A (Signal Extraction)**: Extracts exact symbols (`AuthService`), paths (`src/auth/service.py`), domain terms (`password`, `reset`, `rate`), and action verbs.
- **Stage B (Intent Classification)**: Classifies intent (`feature`, `bug`, `security`, `tests`, `configuration`, `refactor`).
- **Stage C & D (Candidate Generation & Scoring)**: Weighted scoring (`exact_path`, `exact_symbol`, `filename`, `subsystem`, `entry_point`, `test_relation`, `config_relation`). Returns explicit reason for every score.
- **Stage E (Confidence Estimation)**: Computes `high`, `medium`, or `low` based on signal agreement and score separation.
- **Stage F (Progressive Expansion)**:
  - `high`: Primary targets + direct tests + direct configs.
  - `medium`: 1st-order dependencies + adjacent tests.
  - `low`: Subsystem neighbors + extra entry points + targeted grep.
- **Stage G (Read Plan)**: Returns step-by-step reading plan and explicit skip list.

### 3. Source Verification
Read top-ranked files from the read plan. Verify implementation contracts in primary source code.

### 4. Incremental Refresh
After implementing code changes, refresh knowledge incrementally:
```bash
python scripts/refresh_knowledge.py --repo-root /absolute/path/to/repo --changed-file /absolute/path/to/repo/src/auth/service.py --changed-file /absolute/path/to/repo/tests/auth/test_service.py
```
Re-indexes modified files and updates hashes. Triggers full rebuild automatically if change ratio > 20% or schema changed.

### 5. Validation & Benchmark
Validate knowledge integrity:
```bash
python scripts/validate_knowledge.py --repo-root /absolute/path/to/repo
```
Run benchmark harness to measure exploration and token reduction:
```bash
python scripts/benchmark_knowledge.py --repo-root /absolute/path/to/repo --tasks /absolute/path/to/repo/tests/fixtures/benchmark_tasks.json
```
