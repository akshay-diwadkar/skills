# Skills

Agent skills for AI coding assistants. Skills are reusable, self-contained instructions that teach an agent to perform a specific task — planning, diagramming, debugging, etc.

## Structure

Each skill lives in a top-level directory and follows this convention:

```
skill-name/
  SKILL.md           # Required — frontmatter (name, description) + skill instructions
  references/        # Reference docs linked from SKILL.md
  scripts/           # Helper scripts (Python, shell, etc.)
  assets/            # Templates, static files
  agents/            # Sub-agent configs (e.g., openai.yaml)
```

## Usage

Skills in `~/.agents/skills/` are auto-discovered by the agent. To use a skill:

1. **By name** — the agent loads the skill automatically when the task matches its description
2. **By trigger** — skills with a `triggers` field in their frontmatter activate on matching phrases (e.g., `/graphify`)
3. **Manually** — reference a skill in your agent config file (e.g., `opencode.json` or `CLAUDE.md`) under the skills section

## Tracked Skills

### Planning & Design

- **plan-with-senior-dev** — Produce codebase-grounded, decision-complete implementation plans through focused exploration, plan-shaping questions, existing-pattern alignment, domain-doc judgment, and concrete verification. Run `scripts/check_plan_shape.py` and `scripts/check_plan_rubric.py` to validate plan quality.

### Communication & Diagramming

- **create-diagram** — Grilling workflow that questions the user to shared understanding, then produces an Excalidraw-style HTML diagram. Use for architecture maps, relationship graphs, workflow visualizations, or any diagram that benefits from clarifying questions first.

## Tracking Policy

The `.gitignore` ignores everything by default and explicitly un-ignores only `create-diagram/` and `plan-with-senior-dev/`. Only these two skills are tracked in this repo. Other skills may exist locally under `~/.agents/skills/` but are outside version control.
