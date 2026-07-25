---
name: build-codebase-knowledge
description: Build and maintain a compact, deterministic repository-intelligence layer and task resolver to minimize broad repository scans, unnecessary file reads, context-window usage, and stale architectural assumptions. Use when navigating a complex codebase, starting a new task, resolving relevant files, or updating repository knowledge after code changes.
---

# Build Codebase Knowledge

Maintain a compact, evidence-backed repository-intelligence layer (`context.md`, `architecture.md`, `index.json`, `manifest.json`) and run a deterministic multi-stage task resolver to locate target code with minimum token and context overhead.

Source code remains authoritative. Generated knowledge is an index and navigation aid, never a substitute for verifying implementation details.

## Execution Rules

1. **Check Freshness First**: Run `python scripts/cli.py status` before initial exploration.
2. **Run Resolver for Tasks**: Execute `python scripts/cli.py resolve "<task>"` before conducting broad repository searches.
3. **Read Minimum Source Slice**: Follow the resolver's ordered read plan. Read only high-confidence candidates first.
4. **Verify Implementation**: Verify behavior and dynamic details in primary source files before making implementation decisions.
5. **Incremental Refresh After Writes**: Call `python scripts/cli.py refresh --changed-file <file>` immediately after finishing edits.
6. **No-Op Protection**: Do not regenerate fresh artifacts. Do not read every file listed in `index.json`.

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
- `index.json`: Schema-validated index of subsystems, files, symbols, entry points, tests, configs.
- `manifest.json`: Revision metadata, git status, file hashes, freshness state.

Also links knowledge docs in `AGENTS.md` and/or `CLAUDE.md` (or creates them if missing):
```bash
python scripts/link_agent_docs.py --repo-root /absolute/path/to/repo
# or via CLI:
python scripts/cli.py link-docs --repo-root /absolute/path/to/repo
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
