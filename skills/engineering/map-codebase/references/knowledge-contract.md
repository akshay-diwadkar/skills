# Knowledge Contract

## Authority and Artifacts

- Source is authoritative.
- The knowledge directory contains only deterministic machine artifacts.
- Root artifacts are `manifest.json`, `repo-map.json`, `symbols.json`, and `relationships.json`.
- The directory also contains catalogued symbol shards.
- The knowledge directory contains no Markdown orientation artifacts.

## Agent-Document Finalization

- After a successful unified CLI or standalone build/refresh executable, `AGENTS.md` and `CLAUDE.md` each contain one managed MAP-CODEBASE reference.
- The managed reference points to the resolved knowledge directory, including a custom `--output` path.
- Importable `build_knowledge()` and `refresh_knowledge()` are lower-level artifact operations and do not edit instruction files.
- Missing instruction files are created.
- User-owned text outside the managed block is preserved.
- The per-file `<!-- OPT-OUT MAP-CODEBASE -->` marker skips only the file containing it.
- `link-docs` explicitly reapplies the same behavior.
- Finalization plans and validates both instruction-file targets before writing either.
- Each changed instruction file is written through a same-directory temporary file.
- Each changed instruction file is atomically replaced.
- Existing file modes are preserved where supported.
- A two-file commit failure attempts to restore the original bytes of pre-existing files.
- The same rollback attempts to remove files created by the failed transaction.
- A rollback failure is reported as incomplete.
- Knowledge artifacts are retained whenever agent-document finalization fails.

## Agent Mode Permissions

- `status`, `resolve`, `validate`, and direct reads of existing knowledge or source are read-only operations.
- Read-side operations are permitted in plan mode and other modes that prohibit file writes.
- Read-side operations are not gated on whether `AGENTS.md` or `CLAUDE.md` is missing, stale, unwritable, or already contains the managed block.
- `resolve` may use valid existing knowledge at any reported freshness state.
- If knowledge artifacts are missing or invalid in a no-write mode, navigate authoritative source directly rather than requiring a write-side repair.
- `build`, `refresh`, `link-docs`, instruction-file finalization, and `generate-workflow` are write-side operations subject to the active agent mode.

## Freshness States

- `fresh` means the root artifacts and every listed shard hash are valid.
- `fresh` also means that no relevant indexed file changed.
- Revision, branch, dirty state, and configured untracked metadata are compared explicitly.
- A metadata-only difference rewrites only `manifest.json`.
- `partially-stale` means a safe changed-file delta is available.
- `stale`, `missing`, and `invalid` require a full rebuild.
- Refresh takes the full-rebuild path before loading an existing manifest for those states.
- Schema, configuration, or extractor changes require a full rebuild.
- Unsafe artifacts require a full rebuild.
- Repository-wide configuration changes require a full rebuild.
- Configured changed-path-ratio escalation requires a full rebuild.

## Change Detection and Recovery

- The resolved knowledge directory never participates in repository comparisons.
- The exclusion also applies when the directory is selected with `--output`.
- Git status uses a normal diff when available.
- Git uses inventory recovery when the stored revision is unavailable.
- Filesystem inventory is used only when Git is unavailable.
- Unchanged inventory recovery updates metadata only.
- Changed inventory recovery requires a safe full rebuild.

## Untracked Files

- Initial builds include safe untracked files by default.
- Ignored files are excluded.
- Files generated according to configuration are excluded.
- Binary, oversized, secret-sensitive, unsafe, out-of-scope, and knowledge-output files are excluded.
- With `include_untracked = false`, build, status, refresh, dirty state, and explicit changed paths all exclude untracked files.

## Resolver Contract

- Resolver phases are bounded.
- Each task has one deterministic primary owner and optional secondary constraints.
- Active configuration keys receive ranked bounded ranges.
- Test and import evidence always describes the returned target's directional, one-hop relationship.
- The resolver loads only selected symbol shards internally.
- Consumers verify returned source before acting.
- Source remains authoritative.

## Workflow Generation

- Workflow generation remains explicit opt-in.
