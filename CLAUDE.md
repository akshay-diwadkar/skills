# CLAUDE.md

## Repository Knowledge

Before repository exploration, read `.agent/knowledge/KNOWLEDGE.md` and use the `map-codebase` resolver:

* Start at phase 1; read only returned targets and selected symbol shards.
* Expand only when its stop condition is unmet.
* Verify conclusions in current source.

## Skill Design

Before creating, reviewing, or changing a skill, read [SKILL_PHILOSOPHY.md](SKILL_PHILOSOPHY.md) and apply its Change Gate.

## Repository Changes

Before changing skills, packaging, validators, dependencies, runtime requirements, or release configuration, read [REPO_VERSIONING.md](REPO_VERSIONING.md) and follow it exactly. Never merge a PR.

## Benchmark Environment

Before map-codebase benchmark or fixture work, read [REPO_VERSIONING.md](REPO_VERSIONING.md#benchmark-environment) and use its prescribed local environment.
