# Platform Compatibility Matrix

This document provides platform-by-platform details regarding discovery mechanisms, manifest locations, skill/agent support, safety enforcement, and compatibility testing.

---

## 1. Compatibility Summary Table

| Platform | Skills Distributed | Role Agents | Manifest / Adapter Location | Discovery & Installation Mechanism | Status |
| --- | --- | --- | --- | --- | --- |
| **Claude Code** | Yes (`skills/engineering/`) | Yes (`agents/claude/*.md`) | `.claude-plugin/plugin.json`<br>`.claude-plugin/marketplace.json` | Native plugin / Marketplace (`engineering-skills`) | **Supported** (Plugin) |
| **Cursor** | Yes (`skills/engineering/`) | Yes (`agents/cursor/*.md`) | `.cursor-plugin/plugin.json`<br>`.cursor-plugin/marketplace.json` | Native plugin / Explicit `./skills/engineering/...` paths | **Supported** (Plugin) |
| **Codex / OpenAI** | Yes (`skills/engineering/`) | Yes (`.codex/agents/*.toml`) | `.codex/config.toml`<br>`tools/agents/install_codex_agents.py` | Canonical skills / Project-scoped installer script | **Supported** (Project / Installer) |
| **skills.sh** | Yes (`skills/engineering/`) | No (Skills only) | Canonical `skills/*/*/SKILL.md` | `npx skills add akshay-diwadkar/skills` | **Supported** (Skills CLI) |

---

## 2. Platform Details

### Claude Code

- **Discovery Mechanism**: Plugin manifests at `.claude-plugin/plugin.json` and marketplace at `.claude-plugin/marketplace.json`.
- **Skills Support**: Native discovery via `./skills/engineering/<skill-name>` relative paths.
- **Agent Support**: Native agent adapters in `agents/claude/*.md` with explicit tool declarations (`Read`, `Grep`, `Glob`, `Bash`, `WebSearch`, `WebFetch`, `Skill`, `Edit`, `Write`).
- **Safety Controls**: Read-only agents omit `Edit` and `Write` tools; `Bash` execution is governed by tool scoping and prompt-enforced policy.
- **Testing**: Validated against pinned JSON schemas (`claude_plugin_schema.json`, `claude_marketplace_schema.json`) in `validate_repository.py` and `test_platform_agent_manifests.py`.

### Cursor

- **Discovery Mechanism**: Local plugin directory at `~/.cursor/plugins/local/engineering-skills` via `.cursor-plugin/plugin.json`.
- **Skills Support**: Explicit list of `./skills/engineering/<skill-name>` relative paths ensures complete discovery of nested domain skill directories.
- **Agent Support**: Native agent definitions in `agents/cursor/*.md` with frontmatter `readonly` state matching catalog access rules.
- **Safety Controls**: Host-enforced read-only state via `readonly: true` in agent frontmatter.
- **Testing**: Validated against pinned JSON schemas (`cursor_plugin_schema.json`, `cursor_marketplace_schema.json`) in `validate_repository.py` and `test_platform_agent_manifests.py`.

### Codex / OpenAI

- **Discovery Surface Breakdown**:
  | Surface | Skills | Named Agents | Status |
  | --- | --- | --- | --- |
  | Codex project/repository checkout | Yes | Yes, via project config | Supported |
  | Codex explicit project installer | Existing skills | Yes | Supported via installer |
  | Portable skill installation | Yes | No automatic agents | Skills only |
  | Codex app or hosted surfaces | Unverified | Not automatically discovered | Best effort / unverified |
- **Discovery Mechanism**: Project-level `.codex/config.toml` and `.codex/agents/*.toml` files.
- **Skills Support**: Individual skills under `skills/engineering/`.
- **Agent Support**: TOML agent definitions automatically generated from `agents/source/*.md`. Attached to target projects via `tools/agents/install_codex_agents.py`.
- **Safety Controls**: Host-enforced read-only sandbox mode (`sandbox_mode = "read-only"`).
- **Testing**: Automated repository contract tests in `tests/repository/test_codex_agent_installer.py`.

### skills.sh

- **Discovery Mechanism**: Inspects canonical `skills/<domain>/<skill>/SKILL.md` paths.
- **Skills Support**: Full support for all individual skills.
- **Agent Support**: Skills only (`skills.sh` host specification does not define custom agent roles).
- **Testing**: Validated by `tools/validation/validate_repository.py`.

---

## 3. Automated Repository Validation vs. Native Host Verification

Automated CI checks prove repository contract compliance, valid manifest schemas, link integrity, and installed-runtime execution. They do not run native host installations inside proprietary applications. Maintainers execute manual native-host smoke tests before releasing major versions.

---

## 3. Breaking Changes Policy

The following changes require a major version bump in `VERSION`:
- Renaming or removing a stable skill or agent.
- Modifying a canonical skill path.
- Restricting invocation permissions (e.g. changing `both` to `user`).
- Removing supported platform manifests or adapter generators.
