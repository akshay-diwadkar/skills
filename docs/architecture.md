# Repository Architecture

This repository is designed as a production-grade engineering skill monorepo. It organizes skills into canonical runtime definitions with single-source catalog metadata.

---

## 1. Directory Tree

```text
skills/
├── catalog/
│   ├── skills.yaml             # Single source of truth for skill catalog
│   └── skills.schema.json      # JSON Schema for skills.yaml
├── docs/                       # Human-facing documentation & guides
│   └── skills/                 # Per-skill human reference guides
├── skills/
│   └── engineering/            # CANONICAL distributable skills
│       ├── build-codebase-knowledge/
│       ├── codebase-issue-auditor/
│       ├── create-diagram/
│       ├── design-codebase-with-senior-dev/
│       ├── github-issue-planner/
│       ├── implement-with-senior-dev/
│       ├── optimize-codebase-with-senior-dev/
│       └── plan-with-senior-dev/
├── tests/                      # Isolated test suites & live eval runners
│   ├── repository/             # Monorepo contract & catalog sync tests
│   ├── skills/                 # Skill-specific unit & contract tests
│   └── integration/            # Distribution & packaging smoke tests
└── tools/                      # Repository maintenance tooling
    ├── catalog/                # Catalog synchronization & schema validation
    ├── packaging/              # Distribution build & verification
    ├── release/                # Version check & changelog tools
    └── validation/             # Link, dependency, and repository validators
```

---

## 2. Core Architectural Principles

### 1. Single Source of Truth
`catalog/skills.yaml` serves as the machine-readable authoritative registry. Metadata such as domain, maturity status, invocation type, capabilities, and platform support are stored in YAML catalogs rather than directory paths or ad-hoc files.

### 2. Clean Packaging Boundaries
Distributable skill directories (`skills/engineering/<skill-name>/`) contain strictly runtime-required assets (`SKILL.md`, `scripts/`, `templates/`, `references/`). All test suites, benchmarks, evaluation fixtures, and browser smoke test scripts are located outside runtime packages under `tests/`.

### 3. Distribution Building & Verification
Distribution packages are built by `tools/packaging/build_distribution.py` and validated by `tools/packaging/verify_distribution.py`. Packaging verification ensures that zero internal test artifacts or cache files enter distributable archives.

---

## 3. Related Documentation

- [Safety & Controls](safety.md)
- [Platform Compatibility](compatibility.md)
- [Testing Strategy](testing.md)
