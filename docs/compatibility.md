# Platform Compatibility Matrix

This document provides platform-by-platform details regarding discovery mechanisms, manifest locations, skill/agent support, and compatibility testing.

---

## 1. Compatibility Summary Table

| Platform | Skills Distributed | Role Agents | Manifest / Adapter Location | Status |
| --- | --- | --- | --- | --- |
| **Claude Code** | Yes (`skills/engineering/`) | Yes (`agents/claude/*.md`) | `.claude-plugin/plugin.json`<br>`.claude-plugin/marketplace.json` | **Supported** (Plugin) |
| **Cursor** | Yes (`skills/engineering/`) | Yes (`agents/cursor/*.md`) | `.cursor-plugin/plugin.json` | **Supported** (Plugin) |
| **Codex / OpenAI** | Yes (`skills/engineering/`) | Yes (`.codex/agents/*.toml`) | `.codex/config.toml`<br>`tools/agents/install_codex_agents.py` | **Supported** (Project / Installer) |
| **skills.sh** | Yes (`skills/engineering/`) | No (Skills only) | Canonical `skills/*/*/SKILL.md` | **Supported** (Skills CLI) |

---

## 2. Platform Details

### Claude Code

- **Discovery Mechanism**: Plugin manifests at `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`.
- **Skills Support**: Full support. Promoted skills declared in `plugin.json`.
- **Agent Support**: Native agent adapters in `agents/claude/*.md` with explicit tool declarations (`Read`, `Grep`, `Glob`, `Bash`, `WebSearch`, `WebFetch`, `Skill`, `Edit`, `Write`).
- **Known Limitations**: Requires Claude Code plugin marketplace or local plugin load commands.
- **Testing**: Manifest validity checked in `tests/repository/test_platform_agent_manifests.py`.

### Cursor

- **Discovery Mechanism**: Plugin manifest at `.cursor-plugin/plugin.json`.
- **Skills Support**: Discovers skills from `./skills/`.
- **Agent Support**: Native agent definitions in `agents/cursor/*.md` with frontmatter `readonly` state matching catalog access rules.
- **Known Limitations**: Manual or workspace-level symlinking required if marketplace package is not attached.
- **Testing**: Checked in `tests/repository/test_platform_agent_manifests.py`.

### Codex / OpenAI

- **Discovery Mechanism**: Project-level `.codex/config.toml` and `.codex/agents/*.toml` files.
- **Skills Support**: Individual skills under `skills/engineering/`.
- **Agent Support**: TOML agent definitions automatically generated from `agents/source/*.md`. Project attachment available via `tools/agents/install_codex_agents.py`.
- **Known Limitations**: Custom agents require copying TOML files into target project's `.codex/agents/` or running the installer tool.
- **Testing**: Tested in `tests/repository/test_codex_agent_installer.py`.

### skills.sh

- **Discovery Mechanism**: Inspects canonical `skills/<domain>/<skill>/SKILL.md` paths.
- **Skills Support**: Full support for all individual skills.
- **Agent Support**: Skills only (`skills.sh` host specification does not define custom agent roles).
- **Known Limitations**: Installs individual skills into user scope (`~/.agents/skills`); does not register composite agent roles.
- **Testing**: Validated by `tools/validation/validate_repository.py`.

---

## 3. Breaking Changes Policy

The following changes require a major version bump in `VERSION`:
- Renaming or removing a stable skill or agent.
- Modifying a canonical skill path.
- Restricting invocation permissions (e.g. changing `both` to `user`).
- Removing supported platform manifests or adapter generators.
