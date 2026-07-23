# Repository Architecture

This repository is designed as a production-grade engineering skill monorepo. It organizes skills and agents into canonical source definitions, generating host-specific platform adapters automatically.

---

## 1. Directory Tree

```text
skills/
├── .claude-plugin/             # Claude Plugin distribution manifests
├── .codex/                     # Codex agent configuration & generated agent TOML files
├── .cursor-plugin/             # Cursor Plugin distribution manifests
├── agents/
│   ├── source/                 # CANONICAL source agent prompts (markdown)
│   ├── claude/                 # GENERATED Claude Code agent adapters
│   └── cursor/                 # GENERATED Cursor agent adapters
├── catalog/
│   ├── skills.yaml             # Single source of truth for skill catalog
│   ├── skills.schema.json      # JSON Schema for skills.yaml
│   ├── agents.yaml             # Single source of truth for agent catalog
│   └── agents.schema.json      # JSON Schema for agents.yaml
├── docs/                       # Human-facing documentation & guides
│   ├── agents/                 # Per-agent human reference guides
│   └── skills/                 # Per-skill human reference guides
├── skills/
│   └── engineering/            # CANONICAL distributable skills
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
    ├── agents/                 # Agent installation helpers
    ├── catalog/                # Catalog synchronization & schema validation
    ├── packaging/              # Distribution build & verification
    ├── release/                # Version check & changelog tools
    └── validation/             # Link, dependency, and repository validators
```

---

## 2. Core Architectural Principles

### 1. Single Source of Truth
`catalog/skills.yaml` and `catalog/agents.yaml` serve as the machine-readable authoritative registries. Metadata such as domain, maturity status, invocation type, capabilities, and platform support are stored in YAML catalogs rather than directory paths or ad-hoc files.

### 2. Source Agent Prompts & Platform Adapters
- Canonical agent prompt logic is authored once under `agents/source/<agent-name>.md`.
- `tools/catalog/sync_catalog.py` reads `catalog/agents.yaml` and source prompts to automatically generate platform-specific adapters for Claude Code (`agents/claude/`), Cursor (`agents/cursor/`), and Codex (`.codex/agents/`).
- Direct modification of generated platform adapters is strictly prohibited; updates must be made to source prompts or catalog metadata.

### 3. Clean Packaging Boundaries
Distributable skill directories (`skills/engineering/<skill-name>/`) contain strictly runtime-required assets (`SKILL.md`, `scripts/`, `templates/`, `references/`). All test suites, benchmarks, evaluation fixtures, and browser smoke test scripts are located outside runtime packages under `tests/`.

### 4. Distribution Building & Verification
Distribution packages are built by `tools/packaging/build_distribution.py` and validated by `tools/packaging/verify_distribution.py`. Packaging verification ensures that zero internal test artifacts or cache files enter distributable archives.

---

## 3. Related Documentation

- [Safety & Controls](safety.md)
- [Platform Compatibility](compatibility.md)
- [Testing Strategy](testing.md)
