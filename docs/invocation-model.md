# Invocation Model

## Invocation Types

Skill invocation mode determines how agent platforms trigger or expose a skill:

- `user`: Exposed for explicit user invocation only.
- `model`: Exposed for automatic model invocation based on prompt applicability.
- `both`: Support both explicit user invocation and implicit model matching.

## Alignment Rules

Invocation metadata declared in `catalog/skills.yaml` must align with `SKILL.md` frontmatter and any platform-specific agent configurations (e.g. `agents/openai.yaml`).
