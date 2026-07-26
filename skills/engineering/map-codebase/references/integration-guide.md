# Integration Guide

## Standard Workflow

1. Resolve absolute skill and repository paths.
2. Run `status`.
3. Build only when artifacts are missing, invalid, or request a full rebuild.
4. Otherwise run `refresh`.
5. Resolve phase 1 and read only returned source targets.
6. Verify authoritative source.
7. Stop when the phase question is answered.
8. Expand only on an explicit trigger.
9. After one coherent change set, refresh and run `validate`.

## Agent Mode Permissions

- `status`, `resolve`, `validate`, and direct reads of knowledge or source are read-only.
- Read-side operations may run during plan mode and other no-write modes.
- Missing, stale, unwritable, or already-managed `AGENTS.md` and `CLAUDE.md` files do not gate read-side operations.
- Valid existing knowledge may be resolved at any freshness state.
- When knowledge artifacts are missing or invalid in a no-write mode, navigate source directly instead of requiring `build`, `refresh`, or `link-docs`.
- `build`, `refresh`, `link-docs`, agent-document finalization, and `generate-workflow` are write-side operations and must respect the active agent mode.

## Refresh Behavior

- `refresh` applies a safe changed-file delta when available.
- When repository metadata changes without indexed content changes, `refresh` performs a metadata-only manifest refresh.
- Metadata-only refresh rewrites only `manifest.json`.
- Git uses a cheap diff when possible.
- Git uses a one-time inventory recovery when a stored revision cannot be diffed.
- Unchanged inventory recovery can use metadata-only refresh.

## Resolver Usage

- Resolve phase 1 first.
- Read only the returned source targets.
- The resolver loads selected symbol shards internally.
- Agents must not preload symbol shards.
- Mixed implementation tasks are source-first.
- Direct test maintenance is test-owned.
- Configuration requests are configuration-owned.
- Configuration ranges target ranked active keys rather than first textual matches.

## Agent-Document Finalization

- The unified CLI is preferred.
- Successful standalone `build_knowledge.py` and `refresh_knowledge.py` executions provide the same `AGENTS.md` and `CLAUDE.md` finalization postcondition.
- Importing `build_knowledge()` or `refresh_knowledge()` does not edit instruction files.
- Existing content is preserved outside one idempotent managed block.
- Missing instruction files are created.
- `<!-- OPT-OUT MAP-CODEBASE -->` skips only the file containing it.
- `link-docs` remains available for explicit repair.
- Changed instruction files use atomic replacement.
- If the two-file commit fails, finalization attempts to restore the exact pre-operation state.
- Completed knowledge artifacts are retained when instruction-file finalization fails.

## Untracked Files and Knowledge Output

- `include_untracked` is enabled by default for safe, non-ignored working-tree files.
- When disabled, it applies equally to build, status, refresh, and explicit changed paths.
- The knowledge output directory is always internally excluded.
- The exclusion includes dirty state and untracked metadata.

## Workflow Generation

- Workflow generation is explicit opt-in only.
