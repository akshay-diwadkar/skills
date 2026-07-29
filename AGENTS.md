# AGENTS.md

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

`VERSION` is the authoritative suite version. Keep the `version` field in every
`SKILL.md` synchronized with it.

Any modification within a skill package under `skills/<domain>/<skill>/` is a
skill update and requires a Semantic Versioning bump in the same change,
including documentation and supporting resources. Update `VERSION` and the
affected skill's `SKILL.md` version. Because suite versions are synchronized,
update the `version` field in every `SKILL.md` to the same new version.

Choose the bump from the skill update's impact:

- Major: breaking skill behavior, contracts, or compatibility.
- Minor: backward-compatible capabilities or new skills.
- Patch: fixes and installation or distribution metadata corrections.

Repository-only documentation, tests, benchmarks, and CI maintenance outside
skill packages do not require a bump unless they change installation or
distributed behavior. After any required bump, run
`python tools/validation/validate_repository.py` before pushing or opening a
pull request.

## Github

Whenever told to push changes or raise a pull request make sure to monitor the workflow test.
If they fail, fix them and repush the changes.
