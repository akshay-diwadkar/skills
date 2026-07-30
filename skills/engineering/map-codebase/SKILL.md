---
name: map-codebase
description: Map unfamiliar or large repositories into compact machine knowledge and resolve implementation ownership before editing. Use for codebase orientation or structure questions, "where is X implemented?" or "which file handles Y?" navigation, pre-change ownership checks, refreshing knowledge after changes, or setting up AGENTS.md/CLAUDE.md references and scheduled refresh workflows.
version: 1.1.0
---

# Map Codebase

Use compact machine knowledge for navigation. Source is always authoritative.

## Quick Start

1. Resolve absolute skill and repository paths.
2. Check knowledge: `python scripts/cli.py status --repo-root /absolute/repo --format json`
3. Build only if missing, invalid, or stale: `python scripts/cli.py build --repo-root /absolute/repo`
4. Resolve phase 1: `python scripts/cli.py resolve "<task>" --repo-root /absolute/repo --phase 1 --format json`
5. Read only returned targets and verify their source contracts.
6. Expand to phase 2 or 3 only when the result names an expansion trigger.
7. After one coherent change set, refresh and validate.

Use `--compact` for paths, confidence, token estimates, and budget details without scoring evidence.
Use `--budget N` to cap the source ranges returned across requested phases.

### Rules

- Never preload repository maps or symbol shards.
- Do not use `--phase all` except for explicit debugging or human inspection.
- Medium confidence is not verified ownership.
- Missing or stale knowledge never blocks direct source inspection.
- `status`, default `resolve`, and `validate` are read-only.
- `--record-analytics` is opt-in and writes `analytics.jsonl`.
- Build, refresh, analytics, document linking, and workflow generation require write permission.

## Commands

```bash
python scripts/cli.py doctor --repo-root /absolute/repo
python scripts/cli.py build --repo-root /absolute/repo [--dry-run]
python scripts/cli.py status --repo-root /absolute/repo --format json
python scripts/cli.py resolve "<task>" --repo-root /absolute/repo --phase 1 \
  --format json [--compact] [--budget N] [--record-analytics]
python scripts/cli.py refresh --repo-root /absolute/repo --changed-file /absolute/repo/file.py
python scripts/cli.py validate --repo-root /absolute/repo
python scripts/cli.py link-docs --repo-root /absolute/repo
python scripts/cli.py generate-workflow --repo-root /absolute/repo --revision <40-char-sha>
```

<!-- EXTENDED REFERENCE — Read only for edge cases or contract changes -->

## Extractor Coverage

<!-- BEGIN EXTRACTOR COVERAGE -->
| Extractor | Inputs | Coverage |
| --- | --- | --- |
| `python.py` | Python | Full AST extraction |
| `javascript.py` | JavaScript, TypeScript, JSX, TSX | Full tree-sitter extraction |
| `lexical.py` | Go, Rust, Java, C, C++ | Full tree-sitter extraction |
| `csharp.py` | C# | Full tree-sitter extraction |
| `configuration.py` | Repository configuration | Structural metadata and commands |
<!-- END EXTRACTOR COVERAGE -->

Install `requirements.txt` before building. Missing tree-sitter grammars fail with an actionable error.
Tree-sitter extractors provide scope-aware symbols, full-body ranges, and imports.

## Freshness and Scope

- Build when artifacts are missing, invalid, or require a full rebuild.
- Refresh safe changed-file deltas or metadata-only revisions.
- Schema, extractor, configuration, and artifact mismatches require rebuilding.
- Safe non-ignored untracked files are included by default.
- `include_untracked = false` applies to build, status, refresh, and explicit changed files.
- The resolved knowledge directory is excluded from indexing and repository metadata.

Read [Knowledge Contract](references/knowledge-contract.md) for exact freshness semantics.
See the [Worked Example](references/example-walkthrough.md) for a partial-staleness workflow.

## Resolver Contract

- Every resolved task has one `primary_owner`; explicit multi-owner requests may add evidence-backed `co_owners`.
- Plausible but unselected files are `alternatives`, never equal owners.
- `constraints` and `impacts` are separate phase outputs. Legacy `targets` remains the requested-phase projection.
- Resolution status is `resolved`, `ambiguous`, or `abstain`.
- Exact paths and symbols take precedence over task vocabulary.
- Contrastive phrases exclude concepts, subsystems, component types, or roles from ownership.
- Mixed implementation tasks remain source-owned.
- Explicit test creation and test-file work are test-owned.
- Exact symbols use the inverted index; only shortlisted symbol shards are loaded.
- Configuration targets use bounded active structural ranges.
- Relationships are directional and one hop.

Read [Resolver Design](references/resolver-design.md) for scoring and phase construction.
Read [Resolver Benchmark](references/benchmark.md) for measured retrieval quality.

## Agent Documents

- Unified `build` and `refresh` ensure one managed knowledge reference in `AGENTS.md` and `CLAUDE.md`.
- Standalone build and refresh scripts provide the same finalization.
- Importable build and refresh APIs write artifacts only.
- Missing instruction files are created; user content outside managed blocks is preserved.
- `<!-- OPT-OUT MAP-CODEBASE -->` skips one instruction file.
- Two-file finalization failures roll back both instruction files.
- `link-docs` repairs references; `--create-missing` remains a compatibility no-op.

## Workflow Generation

Workflow creation is opt-in and requires an immutable runtime revision:

```bash
python scripts/cli.py generate-workflow --repo-root /absolute/repo \
  --revision <40-character-commit-sha>
```

Normal knowledge commands never create or modify workflows.

## Errors

- Expected operational errors produce concise stderr diagnostics and non-zero exits.
- `status` preserves its machine-readable zero-exit compatibility policy.
- Resolve errors include build and direct-source recovery suggestions.
