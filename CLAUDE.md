# CLAUDE.md

<!-- BEGIN MAP-CODEBASE -->
## Repository Knowledge
Repository knowledge is available under `.agent/knowledge/`.

Use it as the default navigation workflow:
1. Before broad exploration, check freshness.
2. Build or refresh only when knowledge is missing, invalid, or stale.
3. Resolve the current task at phase 1; read only its returned targets and selected symbol shards.
4. Expand to later phases only when phase 1's stop condition is unmet.
5. Verify conclusions in current source, then refresh after a coherent change set.

Do not preload all maps or shards. Knowledge guides navigation; source remains authoritative.
<!-- END MAP-CODEBASE -->

## Versioning

- `VERSION` is the package version. Every change under `skills/<domain>/<skill>/` requires a Semantic Versioning bump in that skill's `SKILL.md` and in `VERSION`; bump only the affected skills, and unmodified skills retain their versions. Use the highest-impact change: Major: breaking behavior or compatibility; Minor: backward-compatible capability; Patch: fixes or distribution corrections.
- When `VERSION` changes, update `VERSION_DESC.md` and the README release-badge cache key. Repository-only tests, docs, benchmarks, and CI need no bump unless they change distributed or installation behavior.
- When validators, their dependencies, skill runtime requirements, or release inputs change, update `tools/validation/release-requirements.txt` and the release-contract tests.
- After changing skill guidance, required reads, manifests, or packaged runtimes, run `python tools/validation/measure_context_load.py --write` and then `python tools/validation/measure_context_load.py --check --compare-ref <base>`; commit the context-load report and any required concise budget exception.
- Before merge, install `tools/validation/release-requirements.txt`, run `python tools/validation/validate_repository.py`, and require `Pre-release Validation` plus all other required checks to pass.
- When pushing or opening a pull request, monitor workflows, fix failures, and repush. After a version change merges, monitor `Publish Release` through completion.
- Run the smallest relevant tests first and expand in proportion to risk; avoid repeating expensive unchanged suites.

## Local Validation Environment

- Install benchmark- and fixture-only Python tools in `.scratch/benchmarks/venv-map-codebase-v2` with `uv`, and prefer its CPython 3.11.11 interpreter for those commands. Recreate the ignored environment when missing or stale; do not add benchmark-only tools to distributed skill requirements.
