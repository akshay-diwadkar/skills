# Knowledge Contract

Source is authoritative. The knowledge directory contains only deterministic machine artifacts: `manifest.json`, `repo-map.json`, `symbols.json`, `relationships.json`, and catalogued symbol shards. It contains no Markdown orientation artifacts.

`fresh` means root artifacts and listed shard hashes are valid and no relevant indexed file changed. A Git revision may change while status remains `fresh` when no indexed content changed; refresh then performs metadata-only manifest update. `partially-stale` has a safe changed-file delta. `stale`, `missing`, and `invalid` require a full rebuild. Schema/config/extractor changes, unsafe artifacts, repository-wide configuration changes, and configured changed-path-ratio escalation also require full rebuild.

Initial builds include safe untracked files by default, excluding ignored, generated-as-configured, binary, oversized, secret-sensitive, unsafe, and out-of-scope files. Resolver phases are bounded; it loads only selected shards internally and consumers verify returned source before acting. Workflow generation remains explicit opt-in and source remains authoritative.
