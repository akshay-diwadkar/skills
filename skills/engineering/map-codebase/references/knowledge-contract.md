# Knowledge Contract

Use this reference when exact artifact, freshness, finalization, or failure semantics matter. Source remains authoritative in every state.

## Authority and Artifacts

The knowledge directory contains machine artifacts: `manifest.json`, `repo-map.json`, `symbols.json`, `symbol-index.json`, `relationships.json`, `evidence-index.json`, and catalogued symbol/evidence shards. Evidence shards are content-addressed by file hash, language, and extractor version, so unchanged files are reused without changing the projected repository map. It also contains static `KNOWLEDGE.md`: concise asset locations and navigation guidance, with no repository-specific state. `KNOWLEDGE.md` is excluded from hashes and freshness. Consumers verify returned source before acting.

## Command and Agent-Mode Contract

| Operation | Access | Contract |
| --- | --- | --- |
| `status`, `resolve`, `validate`, direct reads | Read | Permitted in no-write modes. Missing, stale, unwritable, or already-managed instruction files never gate these operations. |
| `build`, `refresh` | Write | Write knowledge artifacts and finalize instruction files when invoked through the unified CLI or standalone executables. |
| Imported `build_knowledge()`, `refresh_knowledge()` | Write | Update artifacts only; full builds also ensure static `KNOWLEDGE.md`; never edit instruction files. |
| `link-docs` | Write | Explicitly repairs static guidance and instruction-file references. |
| `generate-workflow` | Write | Creates a managed workflow only when explicitly requested. |

When knowledge is missing or invalid in a no-write mode, inspect authoritative source directly. Valid existing knowledge may be resolved at any reported freshness state.

## Agent-Document Finalization

After a successful unified CLI or standalone build/refresh executable, `AGENTS.md` and `CLAUDE.md` each contain the skill-owned `## Repository Knowledge` heading followed by one pointer to the resolved `KNOWLEDGE.md`. Missing files are created, user text outside that section is preserved, and `<!-- OPT-OUT MAP-CODEBASE -->` skips only the containing instruction file. Valid legacy marker blocks migrate on write; markerless duplicate headings are rejected.

Finalization plans and validates the static guide and both instruction files before writing any of them. Each changed file is written through a same-directory temporary file and atomically replaced while preserving existing modes where supported. A commit failure attempts to restore original bytes and remove files created by the failed transaction; incomplete rollback is reported. Knowledge artifacts remain available when finalization fails.

## Freshness State Machine

| State | Meaning | Refresh behavior |
| --- | --- | --- |
| `fresh` | Root artifacts and shard hashes are valid, and no relevant indexed content changed. | A metadata-only difference rewrites only `manifest.json`. |
| `partially-stale` | A safe changed-file delta is available. | Apply an incremental refresh. |
| `stale` | Schema, extractor, indexing configuration, repository-wide configuration, or change-ratio rules require rebuilding. | Rebuild before loading an existing manifest. |
| `missing` | Required artifacts do not exist. | Perform a full build. |
| `invalid` | Artifacts are unsafe, malformed, or inconsistent. | Perform a full rebuild. |

Revision, branch, dirty state, and configured untracked metadata are compared explicitly. The Git index is the canonical tracked inventory; porcelain-v2 with `--no-optional-locks` records staged and working-tree state without refreshing a deliberately stale index. Git uses a normal diff when possible and one inventory-recovery pass when the stored revision is unavailable. Filesystem inventory is used only when Git is unavailable. Unchanged recovery updates metadata only; changed unsafe recovery rebuilds.

## Repository Scope

Initial builds include safe, non-ignored untracked files by default. Generated, binary, oversized, secret-sensitive, unsafe, out-of-scope, and knowledge-output files remain excluded. With `include_untracked = false`, build, status, refresh, dirty state, and explicit changed paths all exclude untracked files.

The resolved knowledge directory never participates in indexing, repository comparisons, dirty state, untracked metadata, inventory fallback, or resolver searches, including when selected with a custom `--output`. Untracked source may be indexed when configured, but cannot become a primary owner unless the request or an explicitly authorized benchmark state asks for it.

## Resolver Contract

Each non-abstained task has one deterministic `primary_owner`; explicit multi-owner requests may add independently supported `co_owners`. Alternatives, constraints, and first-order impacts are distinct result sets. Exact indexed paths and symbols outrank vocabulary. Mixed implementation work remains source-owned; direct test maintenance remains test-owned.

Configuration targets use ranked active keys and bounded structural ranges. Test and import evidence is directional and one hop. Resolver phases remain bounded, and selected symbol shards are loaded internally rather than preloaded by consumers.

Artifact schema 6.0 adds component subtypes, normalized subsystem paths, symbol signatures, type hints, decorators, interfaces, references, control-flow markers, calls, and call relationships. Schema 5.0 knowledge is intentionally stale and must be rebuilt.

## Workflow Generation

Workflow generation is explicit opt-in and requires an immutable runtime revision. Normal knowledge commands never create or modify workflows.
