# Repository Versioning and Validation

Read this file before changing skills, packaging, validators, dependencies, runtimes, benchmarks, or release configuration.

## Branch and Release Authority

* Before implementation, create or switch to a dedicated branch.
* Never merge a pull request.
* Bump only the affected skills once per branch.
* No rebump for CI fixes, review rework, or later pre-merge commits.
* Use the highest-impact change when choosing the bump level.

## Skill Versions

Changes under `skills/<domain>/<skill>/` use Semantic Versioning:

* **Major:** breaking behavior or compatibility.
* **Minor:** backward-compatible capability.
* **Patch:** fixes or distribution corrections.

Update only the affected skills:

* skill `version` in `SKILL.md`;
* matching entry in `VERSION`.

Unmodified skills retain their versions.

Repo-only tests, docs, benchmarks, and CI need no bump unless installation or distributed behavior changes.

## Release Metadata

When `VERSION` changes, update:

* `VERSION_DESC.md`;
* README release-badge cache key.

When validators, dependencies, runtime requirements, or release inputs change, update:

* `tools/validation/release-requirements.txt`;
* affected release-contract tests.

## Context Load

After changing skill guidance, required reads, manifests, or packaged runtimes, run:

```bash
python tools/validation/measure_context_load.py --write
python tools/validation/measure_context_load.py --check --compare-ref <base>
```

Commit the report.

Add an exception only when required. Keep it measured, narrow, justified, and concise.

## Benchmark Environment

For map-codebase benchmark and fixture work:

* use `.scratch/benchmarks/venv-map-codebase-v2`;
* manage it with `uv`;
* prefer its CPython 3.11.11 interpreter;
* recreate it when missing or stale;
* keep it ignored;
* do not add benchmark-only tools to distributed skill requirements.

## Validation

Run the smallest relevant tests first. Expand with risk. Do not repeat expensive unchanged suites.

Before merge readiness:

1. Install release requirements.
2. Run:

```bash
python tools/validation/validate_repository.py
```

3. Require `Pre-release Validation` and all required checks.
4. Monitor workflows after pushes and PR updates.
5. After merged version changes, monitor `Publish Release`.

Release-ready means metadata, focused tests, repository validation, and CI agree.
