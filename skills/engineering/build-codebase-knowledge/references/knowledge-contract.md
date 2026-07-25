# Knowledge Layer Contract & Data Guarantees

## 1. Primary Rule
Source code is always authoritative. Generated knowledge artifacts (`context.md`, `architecture.md`, `repo-map.json`, `symbols.json`, `relationships.json`, `manifest.json`) are navigation indexes and query aids. Agents MUST verify implementation details in primary source files before taking action.

## 2. Invariants
- **Deterministic output**: Given identical source tree and configuration, generated artifacts produce identical JSON structure and content hashes.
- **Zero secrets**: Password strings, private keys, environment tokens, and credentials MUST NEVER be included in artifacts. `.env.example` is indexed solely as schema metadata.
- **Conciseness limits**:
  - `context.md`: <=120 lines default (<=180 for monorepos).
  - `architecture.md`: <=220 lines default (<=320 for monorepos).
- **Exact identifiers**: Function names, class names, file paths, and environment variable names must preserve exact casing and punctuation.

## 3. Freshness Lifecycle States
- `fresh`: Git revision match, zero changed tracked files.
- `partially-stale`: Modified files detected; incremental refresh pending.
- `stale`: Revision mismatch (branch switch / rebase) or >20% changed files.
- `invalid`: Broken schema, invalid JSON, or missing mandatory files.
