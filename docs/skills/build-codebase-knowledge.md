# build-codebase-knowledge

Generate and maintain a compact, deterministic repository-intelligence layer and task resolver to minimize broad repository scans, unnecessary file reads, context-window usage, and stale architectural assumptions.

## Overview

The `build-codebase-knowledge` skill equips AI coding agents with a structured, versioned index of a repository (`context.md`, `architecture.md`, `index.json`, and `manifest.json`) and a deterministic multi-stage task resolver.

Key capabilities:
1. **Compact orientation**: `context.md` (60–120 lines) & `architecture.md` (100–220 lines).
2. **Deterministic Task Resolver**: Analyzes task intent, scores candidates using weighted repository signals, and outputs an ordered read plan with progressive expansion.
3. **Cheap Freshness & Incremental Refresh**: Verifies Git revision/diff and re-indexes only changed files on implementation finish.
4. **Validation & Benchmark Suite**: Schema verification, conciseness audits, secret exclusion, and token reduction metrics.

## CLI Usage

```bash
# Build initial repository knowledge
python skills/engineering/build-codebase-knowledge/scripts/cli.py build --repo-root .

# Resolve a natural language task
python skills/engineering/build-codebase-knowledge/scripts/cli.py resolve "Add rate limiting to password reset" --format human

# Refresh incrementally after changes
python skills/engineering/build-codebase-knowledge/scripts/cli.py refresh --changed-file src/auth/service.py

# Validate knowledge status
python skills/engineering/build-codebase-knowledge/scripts/cli.py validate

# Run benchmark suite
python skills/engineering/build-codebase-knowledge/scripts/cli.py benchmark --tasks tests/skills/build-codebase-knowledge/fixtures/benchmark_tasks.json
```

## Generated Artifacts

Artifacts default to `.agent/knowledge/`:
- `context.md`: High-density repository map & commands.
- `architecture.md`: Boundary matrix, runtime flows, and risk points.
- `index.json`: Schema-validated machine index of subsystems, files, symbols, entry points, and test mappings.
- `manifest.json`: Freshness metadata, file hashes, and delta tracking.
