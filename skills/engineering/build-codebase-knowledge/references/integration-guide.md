# Integration Guide

1. Resolve absolute paths and run `status`.
2. Build only when artifacts are missing, invalid, or request a full rebuild.
3. Otherwise run `refresh`: it applies a safe delta, or a metadata-only revision refresh when indexed content is unchanged.
4. Resolve phase 1 and read only returned targets. The resolver loads the selected symbol shards internally; agents must not preload shards.
5. Verify authoritative source, stop when the phase question is answered, and expand only on an explicit trigger.
6. After one coherent change set, refresh and run `validate`.

`include_untracked` is enabled by default for safe, non-ignored working-tree files. The changed-path ratio selects full versus incremental refresh; it is not a freshness state. Workflow generation is explicit opt-in only.
