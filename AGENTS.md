# AGENTS.md

## Repository Knowledge
Read `.agent/knowledge/KNOWLEDGE.md` before repository exploration.

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
