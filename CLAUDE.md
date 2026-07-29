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

`VERSION` is the authoritative suite version. Keep the `version` field in every
`SKILL.md` synchronized with it.

Apply Semantic Versioning to user-facing changes:

- Major: breaking skill behavior, contracts, or compatibility.
- Minor: backward-compatible capabilities or new skills.
- Patch: fixes and installation or distribution metadata corrections.

Documentation, tests, benchmarks, and CI-only maintenance do not require a bump
unless they change installation or distributed behavior. Update `VERSION` and
all skill versions in the same change, then run
`python tools/validation/validate_repository.py` before pushing or opening a
pull request.

## Github

Whenever told to push changes or raise a pull request make sure to monitor the workflow test.
If they fail, fix them and repush the changes.
