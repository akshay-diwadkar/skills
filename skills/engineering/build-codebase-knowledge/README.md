# build-codebase-knowledge Skill

Production-grade reusable AI agent skill for repository intelligence, compact orientation artifacts, and deterministic task resolution.

## Package Structure

```text
build-codebase-knowledge/
├── SKILL.md
├── README.md
├── scripts/
│   ├── __init__.py
│   ├── build_knowledge.py
│   ├── resolve_task.py
│   ├── refresh_knowledge.py
│   ├── validate_knowledge.py
│   ├── benchmark_knowledge.py
│   └── cli.py
├── schemas/
│   ├── index.schema.json
│   ├── resolver-result.schema.json
│   └── manifest.schema.json
├── templates/
│   ├── context.template.md
│   └── architecture.template.md
└── references/
    ├── knowledge-contract.md
    ├── resolver-design.md
    └── integration-guide.md
```

## Quick Start

```bash
# Build initial artifacts
python scripts/cli.py build --repo-root .

# Resolve task
python scripts/cli.py resolve "Fix session expiration in auth service"

# Check status
python scripts/cli.py status

# Refresh changed files
python scripts/cli.py refresh --changed-file src/auth/service.py

# Validate knowledge
python scripts/cli.py validate
```
