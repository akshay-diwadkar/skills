# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-07-23

### Added

- Restructured repository into canonical domain layout under `skills/engineering/`.
- Created authoritative repository catalog (`catalog/skills.yaml` and `catalog/skills.schema.json`).
- Added catalog synchronization and validation tooling (`tools/catalog/sync_catalog.py`, `validate_catalog.py`).
- Added consolidated repository validation (`tools/validation/validate_repository.py`).
- Added packaging build and verification tooling (`tools/packaging/build_distribution.py`, `verify_distribution.py`).
- Created Claude Plugin manifest (`.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`).
- Added comprehensive maintainer and skill documentation under `docs/`.
- Added Architectural Decision Records (`.agents/adr/0001-repository-architecture.md`, `0002-canonical-skill-catalog.md`, `0003-skill-lifecycle-and-versioning.md`).
