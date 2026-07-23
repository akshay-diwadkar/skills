# Authoring Skills & Agents

This document details how to author, register, test, and document new engineering skills and role agents in this monorepo.

---

## 1. Skill Package Anatomy

Skills reside exclusively under `skills/<domain>/<skill-name>/`. A valid skill package contains:

```text
skills/engineering/my-new-skill/
├── SKILL.md                 # Required: Skill instructions with YAML frontmatter
├── scripts/                 # Optional: Bundled helper scripts (e.g. check_env.py)
├── templates/               # Optional: Output templates or scaffold files
└── references/              # Optional: In-depth reference guides
```

*Note*: Test files, benchmarks, or fixture data MUST NOT be placed inside `skills/`. They belong in `tests/skills/my-new-skill/`.

---

## 2. Step-by-Step Authoring Workflow

### Step 1: Create Skill Folder & `SKILL.md`
Create `skills/engineering/<skill-name>/SKILL.md` with valid YAML frontmatter:

```markdown
---
name: my-new-skill
description: Concise, high-level summary of what this skill does and when to use it.
---

# My New Skill Title

Detailed instructions for the AI assistant...
```

### Step 2: Implement Bundled Scripts
If your skill uses bundled scripts (e.g., environment checkers or report formatters), place them in `skills/engineering/<skill-name>/scripts/`.

### Step 3: Register in Catalog (`catalog/skills.yaml`)
Add an entry to `catalog/skills.yaml`:

```yaml
  - name: my-new-skill
    path: skills/engineering/my-new-skill
    domain: engineering
    status: stable
    kind: workflow           # workflow | discipline | utility
    invocation: both         # user | model | both
    summary: Concise, high-level summary.
    platforms:
      skills_sh: true
      claude_plugin: true
      cursor_plugin: true
      codex: true
    relationships:
      invokes: []
      complements: []
      supersedes: []
    documentation: docs/skills/my-new-skill.md
    tests: tests/skills/my-new-skill
```

### Step 4: Create Human Documentation
Create `docs/skills/my-new-skill.md` providing user guidance, example prompts, input requirements, and expected outputs.

### Step 5: Implement Test Suite
Create unit and contract tests under `tests/skills/my-new-skill/`:

```text
tests/skills/my-new-skill/
├── unit/                    # Pytest unit tests for bundled scripts
├── contract/                # Output format & contract tests
└── fixtures/                # Disposable test fixtures
```

### Step 6: Attach to Role Agents (Optional)
If the new skill belongs to a role-based agent, add it to `catalog/agents.yaml` under the appropriate agent's `skills:` list and update the agent's source prompt under `agents/source/<agent-name>.md`.

### Step 7: Synchronize & Validate
Run catalog sync and repository validation:

```bash
python tools/catalog/sync_catalog.py --write
python tools/validation/validate_repository.py
python tools/validation/validate_links.py
python -m pytest -q
```
