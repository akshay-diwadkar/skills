# Repository Versioning and Validation

Read this file before changing skills, packaging, validators, dependencies, runtimes, benchmarks, or release configuration.

## Branch and Release Authority

* Create or switch to a dedicated branch before implementation.
* Never merge a pull request.
* Version only affected skills.
* Determine each version from the final user-visible diff against the merge base.
* Set the version once after the implementation scope is stable.
* Do not increment it again for CI fixes, review rework, or later pre-merge commits unless the required Semantic Versioning level changes.
* If the required level changes, recalculate from the version on the merge base.
* Use the highest-impact applicable change.

## Skill Versions

Changes under `skills/<domain>/<skill>/` use Semantic Versioning:

* **Major:** breaks a previously supported behavior, input, output, workflow, integration, or compatibility guarantee.
* **Minor:** adds a backward-compatible capability.
* **Patch:** corrects behavior or distribution without breaking previously supported use.
* **None:** does not affect observable skill behavior or distribution.

Update only the affected skills:

* the skill `version` in `SKILL.md`;
* the matching entry in `VERSION`.

Unmodified skills retain their versions.

Repo-only tests, documentation, benchmarks, formatting, and CI changes require no bump unless they change installation, packaging, release output, or distributed behavior.

If implementation scope is narrowed, lower or remove any provisional bump so the final version accurately represents the delivered change.

## Release Metadata

When `VERSION` changes, update:

* `VERSION_DESC.md`;
* the README release-badge cache key.

When validators, dependencies, runtime requirements, or release inputs change, update:

* `tools/validation/release-requirements.txt`;
* affected release-contract tests.

Keep skill version values synchronized. Treat the skill version in `SKILL.md` as authoritative unless repository tooling defines another source of truth.

## Context Load

After changing skill guidance, required reads, manifests, or packaged runtimes, run:

```bash
python tools/validation/measure_context_load.py --write
python tools/validation/measure_context_load.py --check --compare-ref <base>
```

Commit the generated report.

Add an exception only when necessary. Keep it measured, narrow, justified, and concise.

## Benchmark Environment

For `map-codebase` benchmark and fixture work:

* use `.scratch/benchmarks/venv-map-codebase-v2`;
* manage it with `uv`;
* prefer its CPython 3.11.11 interpreter;
* recreate it when missing or stale;
* keep it ignored;
* do not add benchmark-only tools to distributed skill requirements.

## Validation

Run the smallest relevant tests first. Expand in proportion to risk. Do not repeat expensive unchanged suites.

Repository guards such as `test_skill_metadata_and_tracked_references_use_canonical_names_only`
scan only Git-tracked files (`git ls-files`). When a change adds or modifies
tracked artifacts (reports, fixtures, JSON, generated files), re-run the
tracked-file guard suites and repository validation after `git add` and before
pushing:

```bash
python -m pytest tests/repository -q
python tools/validation/validate_repository.py
```

Before declaring merge readiness:

1. Install release requirements.
2. Run:

```bash
python tools/validation/validate_repository.py
```

3. Require `Pre-release Validation` and all other required checks to pass.
4. Monitor workflows after pushes and pull-request updates.
5. After merged version changes, monitor `Publish Release`.

A change is release-ready only when metadata, focused tests, repository validation, and CI agree.
