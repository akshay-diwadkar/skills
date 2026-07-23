# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-07-23

### Fixed & Hardened

- **Claude Plugin & Marketplace Manifest Compliance**: Updated `.claude-plugin/plugin.json` to use official `author` object instead of unsupported `publisher` field, and prefixed component paths with `./`. Added required `owner` metadata to `.claude-plugin/marketplace.json`.
- **Cursor Skill Discovery & Marketplace Manifest**: Refactored `.cursor-plugin/plugin.json` to explicitly list exact `./skills/engineering/<skill-name>` relative paths for all Cursor-enabled skills, ensuring full discovery of nested domain skill directories. Created a distinct Cursor marketplace manifest (`.cursor-plugin/marketplace.json`) conforming to Cursor's schema.
- **Strict Schema Validation**: Created pinned JSON schemas (`claude_plugin_schema.json`, `claude_marketplace_schema.json`, `cursor_plugin_schema.json`, `cursor_marketplace_schema.json`) under `tools/validation/schemas/` and integrated `jsonschema` validation into `validate_repository.py` and `test_platform_agent_manifests.py`.
- **Installed-Runtime Script Resolution**: Updated all `SKILL.md` files to reference bundled scripts via portable `<skill-dir>/scripts/` syntax (resolving via `${CLAUDE_SKILL_DIR:-${CURSOR_SKILL_DIR:-${SKILL_DIR}}}`). Verified that bundled Python scripts resolve internal contracts and templates relative to `Path(__file__).resolve().parent`. Added cross-repository integration tests (`tests/integration/test_installed_skill_execution.py`).
- **Accurate Safety Model Documentation**: Updated `docs/safety.md`, `docs/compatibility.md`, and `README.md` to clearly distinguish host-enforced read-only restrictions (Cursor `readonly: true`, Codex `sandbox_mode = "read-only"`) from tool-scoped and prompt-enforced policy restrictions (Claude Code omitting `Edit`/`Write` tools while retaining `Bash` for non-mutating inspection).
- **CI Workflow Alignment**: Updated GitHub Actions workflows (`quality.yml`, `repository-contract.yml`, `release-check.yml`) matrix to align with Python 3.11+ requirements and execute the complete verification suite.

### Added

- Restructured repository into canonical domain layout under `skills/engineering/`.
- Created authoritative repository catalog (`catalog/skills.yaml` and `catalog/agents.yaml`).
- Added catalog synchronization and validation tooling (`tools/catalog/sync_catalog.py`, `validate_catalog.py`).
- Added consolidated repository validation (`tools/validation/validate_repository.py`).
- Added packaging build and verification tooling (`tools/packaging/build_distribution.py`, `verify_distribution.py`).
- Added comprehensive maintainer and skill documentation under `docs/`.
- Added Architectural Decision Records (`.agents/adr/0001-repository-architecture.md`, `0002-canonical-skill-catalog.md`, `0003-skill-lifecycle-and-versioning.md`).
