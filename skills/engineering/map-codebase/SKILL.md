---
name: map-codebase
description: Build and use compact repository knowledge for resolver-first code navigation. Use when starting coding work in an unfamiliar or large repository, locating likely implementation ownership, or refreshing repository knowledge after a coherent change set.
---

# Map Codebase

Use compact machine-only repository knowledge to reduce exploration overhead while preserving source as authoritative.

## Core Workflow

1. Resolve absolute skill and repository paths.
2. Run `python scripts/cli.py status --repo-root /absolute/path/to/repo --format json`.
3. Build only when artifacts are missing, invalid, or require a full rebuild. Otherwise refresh a safe delta or metadata-only revision.
4. Resolve phase 1 and read only its returned targets. The resolver loads selected symbol shards internally.
5. Verify behavior in authoritative source, then stop when the phase question is answered.
6. Request phase 2 or 3 only for an explicit expansion trigger.
7. Perform the coding task.
8. After one coherent change set, refresh and validate.

## Agent Mode Permissions

### Read-side operations

- `status`, `resolve`, `validate`, and direct reads of existing knowledge or source are read-only operations.
- Read-side operations are permitted during plan mode and any other agent mode that prohibits file writes.
- Read-side operations are not gated on the freshness, presence, writability, or managed-block state of `AGENTS.md` or `CLAUDE.md`.
- Use `resolve` with valid existing knowledge at whatever freshness state is available.
- When knowledge artifacts are missing or invalid and the current mode prohibits writes, inspect authoritative source directly instead of requiring `build`, `refresh`, or `link-docs`.
- Stale or missing knowledge never changes the rule that source is authoritative.

### Write-side operations

- `build` writes knowledge artifacts and finalizes `AGENTS.md` and `CLAUDE.md`.
- `refresh` writes knowledge artifacts and finalizes `AGENTS.md` and `CLAUDE.md`.
- `link-docs` writes the managed references in `AGENTS.md` and `CLAUDE.md`.
- `generate-workflow` writes a managed GitHub workflow.
- Run these write-side operations only when the current agent mode permits file writes.
- Importable `build_knowledge()` and `refresh_knowledge()` are lower-level artifact-only write APIs.

## Freshness Rules

- Build when artifacts are missing, invalid, or require a full rebuild.
- Otherwise use `refresh` for a safe changed-file delta or metadata-only revision.
- `refresh` rebuilds missing, invalid, stale, and otherwise unsafe artifacts before reading a manifest.
- After one coherent change set, refresh and validate.

See [Worked Example](references/example-walkthrough.md) for an actual `partially-stale` status, its refresh command, and a phase-1 resolver result.

## Task Ownership Rules

- Every task has one deterministic primary owner and may have optional secondary constraints.
- Exact indexed paths and symbols take precedence over task vocabulary.
- Mixed implementation tasks remain source-first.
- Test creation, direct test maintenance, and explicit test-file work are test-owned.

## Configuration Ranges and Relationships

- Configuration targets use bounded active structural ranges.
- TOML and INI targets are bounded to active sections.
- YAML and JSON targets are bounded by ancestry.
- Make targets are bounded to their active target ranges.
- All relationship evidence is directional.
- All relationship evidence is one-hop only.

## Repository Scope and Untracked Files

- `include_untracked = false` applies uniformly to build, status, refresh, and explicit `--changed-file` paths.
- The resolved knowledge directory is always excluded from repository metadata.
- The exclusion applies to the default directory and a custom `--output` directory.
- The knowledge directory is also excluded from indexing, change detection, inventory fallback, and resolver searches.
- These exclusions apply even when the knowledge directory is not ignored by the repository.

## Resolver Boundaries

- Use phase 1 first.
- Request phase 2 or 3 only when an explicit expansion trigger applies.
- Use `--phase all` only for explicit debugging or human inspection.
- Do not preload repository maps or symbol shards.
- Read only the source targets returned for the active phase.
- The resolver loads selected symbol shards internally.

## CLI Errors

- Expected CLI operational errors use concise stderr diagnostics.
- Expected CLI operational errors exit with a non-zero status.
- `status` preserves its machine-readable zero-exit compatibility policy.

## Skill Directory Resolution

- Resolve this skill directory before invoking bundled scripts.
- Use the resolved skill directory as the command base.
- Do not assume the current working directory is the skill directory.

## Commands

```bash
python scripts/cli.py build --repo-root /absolute/path/to/repo
python scripts/cli.py status --repo-root /absolute/path/to/repo --format json
python scripts/cli.py resolve "<task>" --repo-root /absolute/path/to/repo --phase 1 --format json
python scripts/cli.py refresh --repo-root /absolute/path/to/repo --changed-file /absolute/path/to/repo/src/example.py
python scripts/cli.py validate --repo-root /absolute/path/to/repo
```

The unified CLI is the preferred interface.

## Agent-Document Finalization

- Successful unified CLI `build` and `refresh` commands ensure `AGENTS.md` and `CLAUDE.md` each contain one current managed repository-knowledge reference.
- Successful standalone `scripts/build_knowledge.py` and `scripts/refresh_knowledge.py` executions provide the same finalization.
- Importable `build_knowledge()` and `refresh_knowledge()` remain lower-level artifact-only APIs and do not finalize instruction files.
- Missing `AGENTS.md` and `CLAUDE.md` files are created.
- User content outside the managed block is preserved.
- Custom `--output` paths are reflected in the managed reference.
- Add `<!-- OPT-OUT MAP-CODEBASE -->` to either existing file to skip only that file.
- Changed instruction files are atomically replaced per file.
- A failed two-file commit rolls back both instruction files to their pre-operation state.
- Knowledge artifacts remain available when instruction-file finalization fails.
- `link-docs` explicitly repairs or reapplies the references.
- `link-docs` always creates missing supported files.
- `link-docs --create-missing` remains accepted as a compatibility no-op.

## Workflow Generation

To explicitly add a managed GitHub refresh workflow, provide an immutable runtime revision:

```bash
python scripts/cli.py generate-workflow --repo-root /absolute/path/to/repo \
  --revision <40-character-commit-sha>
```

- Workflow generation is opt-in.
- Normal knowledge commands never create or modify workflows.

## Common Mistakes

- Do not preload symbol shards; the resolver loads selected shards internally.
- Do not run `--phase all` outside explicit debugging or human inspection.
- Do not treat a stale instruction-file reference as a reason to block `status`, `resolve`, or source reads.
- Do not force a write in plan or read-only mode when knowledge is missing; fall back to authoritative source.
- Do not skip refresh after edits; stale knowledge silently reduces resolver accuracy.
