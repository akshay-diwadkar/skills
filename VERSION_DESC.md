# map-codebase resolver guidance in agent documents

`map-codebase` 2.4.2 now inserts concise resolver navigation guidance alongside the knowledge location in `AGENTS.md` and `CLAUDE.md`. Generated instruction sections direct agents to use the resolver as the default navigation entry point, start at phase 1, read only returned targets and selected symbol shards, expand only when the stop condition is unmet, and verify conclusions in current source. The generated `KNOWLEDGE.md` workflow and focused regression tests enforce the same behavior.
