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

`VERSION` is the authoritative overall skills-package version. Individual
`SKILL.md` versions are independent and do not have to match `VERSION`.

Any modification within a skill package under `skills/<domain>/<skill>/` is a
skill update and requires a Semantic Versioning bump in the same change,
including documentation and supporting resources. Update only the affected
skill's `SKILL.md` version; unmodified skills retain their existing versions.
Every skill update also requires a `VERSION` bump for the overall package. When
multiple skills change in one release, choose the package bump from the
highest-impact skill update.

Whenever `VERSION` changes, update `VERSION_DESC.md` with the GitHub release
summary and update the README release-badge cache key to match. Merging that
change to `main` publishes the matching release automatically.

Choose the bump from the skill update's impact:

- Major: breaking skill behavior, contracts, or compatibility.
- Minor: backward-compatible capabilities or new skills.
- Patch: fixes and installation or distribution metadata corrections.

Repository-only documentation, tests, benchmarks, and CI maintenance outside
skill packages do not require a skill or package bump unless they change
installation or distributed behavior. After any required bump, run
`python tools/validation/validate_repository.py` before pushing or opening a
pull request.

## Release validation

Before merging any pull request, require the `Pre-release Validation` workflow
to pass. Do not merge a version-changing pull request while any required check
is failing.

When a change adds or removes a validator, validator dependency, skill runtime
requirement, or release input, update
`tools/validation/release-requirements.txt` in the same pull request. Keep the
pre-release and publish workflows on that shared requirements file. Add or
update repository tests that verify the release contract.

Run the release validation path before merge:

```bash
python -m pip install -r tools/validation/release-requirements.txt
python tools/validation/validate_repository.py
```

After merging a version change, monitor `Publish Release` through completion.
If it fails, inspect the workflow logs, fix the root cause, and rerun the
workflow only after the fix reaches `main`.

## Github

Whenever told to push changes or raise a pull request make sure to monitor the workflow test.
If they fail, fix them and repush the changes.
