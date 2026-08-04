# CLAUDE.md

## Repository Knowledge
Read `.agent/knowledge/KNOWLEDGE.md` before repository exploration.

## Versioning

- Before implementation, create or switch to a dedicated branch. Bump each affected skill once for the branch's cumulative change; never bump again for CI fixes, review rework, or later commits before merge.
- Changes under `skills/<domain>/<skill>/` follow Semantic Versioning; bump only the affected skills in `SKILL.md` and `VERSION`, while unmodified skills retain their versions. Use the highest-impact change: Major: breaking; Minor: backward-compatible capability; Patch: fixes/distribution. Repo-only tests, docs, benchmarks, and CI need no bump unless distribution or installation behavior changes.
- When `VERSION` changes, update `VERSION_DESC.md` and the README release-badge cache key.
- If validators, dependencies, runtime requirements, or release inputs change, update `tools/validation/release-requirements.txt` and release-contract tests.
- After changing skill guidance, required reads, manifests, or packaged runtimes, run `python tools/validation/measure_context_load.py --write`, then `python tools/validation/measure_context_load.py --check --compare-ref <base>`; commit the report and any required concise budget exception.
- Before merge, install release requirements, run `python tools/validation/validate_repository.py`, and require `Pre-release Validation` plus all required checks. Monitor workflows after pushes/PRs and `Publish Release` after merged version changes.
- Run the smallest relevant tests first; expand with risk and avoid repeating expensive unchanged suites.

## Local Validation Environment

- Install benchmark- and fixture-only Python tools in `.scratch/benchmarks/venv-map-codebase-v2` with `uv`, and prefer its CPython 3.11.11 interpreter for those commands. Recreate the ignored environment when missing or stale; do not add benchmark-only tools to distributed skill requirements.
