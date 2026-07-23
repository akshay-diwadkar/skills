# Installation Guide

This plugin supports multiple AI coding platforms. Follow the instructions for your target host environment.

---

## 1. Claude Code

Claude Code supports installing plugins directly from marketplace repositories or local workspace directories.

### Marketplace Installation (Recommended)

Add the marketplace source and install the plugin:

```bash
# Add the marketplace repository source
/plugin marketplace add akshay-diwadkar/skills

# Install the engineering-skills plugin
/plugin install engineering-skills
```

### Local Development Installation

To load the plugin locally from a cloned repository during development:

```bash
# From within your target repository or workspace
/plugin load /path/to/cloned/skills
```

### Updating & Uninstallation

```bash
# Update installed plugins
/plugin update engineering-skills

# Remove the plugin
/plugin uninstall engineering-skills
```

---

## 2. Cursor

Cursor supports custom agent configurations and skill discovery via `.cursor-plugin/plugin.json`.

### Repository / Local Installation

1. Clone or symlink this repository into your project or user skills folder:
   - User scope: `~/.cursor/plugins/engineering-skills`
   - Workspace scope: `<your-project>/.cursor-plugin`
2. Cursor automatically detects the plugin manifest at `.cursor-plugin/plugin.json` and exposes bundled agents (`agents/cursor/*.md`) and skills (`skills/engineering/`).

### Verification

Open Cursor and verify that custom role agents (such as `architecture-engineer` and `delivery-engineer`) appear in the prompt context or agent selection dropdown.

---

## 3. Codex / OpenAI

Codex and OpenAI-compatible environments discover skills from canonical path definitions (`skills/engineering/`) and role agents from `.codex/agents/*.toml`.

### Single Project Setup via Installer Tool

Use the repository's bundled installer script to attach role-based Codex agents to a target project:

```bash
python tools/agents/install_codex_agents.py --target /path/to/your/project --write
```

This creates `.codex/agents/` in the target project containing TOML agent definitions (`architecture-engineer.toml`, `delivery-engineer.toml`, `issue-resolution-engineer.toml`, `codebase-health-engineer.toml`).

### Manual Codex Configuration

Include `.codex/config.toml` and `.codex/agents/*.toml` in your repository root:

```toml
# .codex/config.toml
[agents]
max_concurrent_threads_per_session = 4
```

---

## 4. skills.sh (Portable Skill Host)

`skills.sh` provides a portable CLI for installing individual skills into agent environments (`~/.agents/skills`).

### Install All Skills Interactively

```bash
npx skills add akshay-diwadkar/skills
```

### Install Specific Skills

```bash
npx skills add akshay-diwadkar/skills --skill plan-with-senior-dev
npx skills add akshay-diwadkar/skills --skill implement-with-senior-dev
npx skills add akshay-diwadkar/skills --skill codebase-issue-auditor
```

### Updating & Removing

```bash
# Update skills
npx skills update

# Remove a skill
npx skills remove plan-with-senior-dev
```

---

## 5. Manual Clone & Symlink Installation

If your host environment does not support automated plugin loading or CLI installation, clone the repository and link individual skills manually.

### Linux / macOS

```bash
git clone https://github.com/akshay-diwadkar/skills.git
cd skills
mkdir -p ~/.agents/skills

# Symlink individual canonical skills
ln -s "$PWD/skills/engineering/plan-with-senior-dev" ~/.agents/skills/
ln -s "$PWD/skills/engineering/implement-with-senior-dev" ~/.agents/skills/
ln -s "$PWD/skills/engineering/codebase-issue-auditor" ~/.agents/skills/
ln -s "$PWD/skills/engineering/github-issue-planner" ~/.agents/skills/
ln -s "$PWD/skills/engineering/design-codebase-with-senior-dev" ~/.agents/skills/
ln -s "$PWD/skills/engineering/optimize-codebase-with-senior-dev" ~/.agents/skills/
ln -s "$PWD/skills/engineering/create-diagram" ~/.agents/skills/
```

### Windows PowerShell (Developer Mode / Administrator)

```powershell
git clone https://github.com/akshay-diwadkar/skills.git
cd skills
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.agents\skills"

New-Item -ItemType SymbolicLink -Path "$env:USERPROFILE\.agents\skills\plan-with-senior-dev" -Target "$PWD\skills\engineering\plan-with-senior-dev"
New-Item -ItemType SymbolicLink -Path "$env:USERPROFILE\.agents\skills\implement-with-senior-dev" -Target "$PWD\skills\engineering\implement-with-senior-dev"
New-Item -ItemType SymbolicLink -Path "$env:USERPROFILE\.agents\skills\codebase-issue-auditor" -Target "$PWD\skills\engineering\codebase-issue-auditor"
New-Item -ItemType SymbolicLink -Path "$env:USERPROFILE\.agents\skills\github-issue-planner" -Target "$PWD\skills\engineering\github-issue-planner"
New-Item -ItemType SymbolicLink -Path "$env:USERPROFILE\.agents\skills\design-codebase-with-senior-dev" -Target "$PWD\skills\engineering\design-codebase-with-senior-dev"
New-Item -ItemType SymbolicLink -Path "$env:USERPROFILE\.agents\skills\optimize-codebase-with-senior-dev" -Target "$PWD\skills\engineering\optimize-codebase-with-senior-dev"
New-Item -ItemType SymbolicLink -Path "$env:USERPROFILE\.agents\skills\create-diagram" -Target "$PWD\skills\engineering\create-diagram"
```

Restart your coding agent or IDE after installing or updating skills.

---

## 6. Installed-Runtime Script Resolution

Skills invoke bundled scripts (such as scaffolders, finalizers, and validators) during execution. When a skill is installed into a user's environment:

- **Host-Native Variables**: Platforms that support skill-directory environment variables set `${CLAUDE_SKILL_DIR}` (Claude Code) or `${CURSOR_SKILL_DIR}` / `${SKILL_DIR}` (Cursor / portable hosts) pointing to the installed skill's directory path.
- **Portable Resolution Syntax**: In `SKILL.md` instructions, script execution commands use:
  ```bash
  python "<skill-dir>/scripts/finalize_plan.py" --tier <tier> --repo-root <repo> <draft>
  ```
  where `<skill-dir>` resolves to the absolute path of the skill's installation directory (or `${CLAUDE_SKILL_DIR:-${CURSOR_SKILL_DIR:-${SKILL_DIR}}}`).
- **Internal Asset Resolution**: Bundled Python scripts locate internal contracts, assets, and templates relative to `Path(__file__).resolve().parent`. Commands execute cleanly regardless of whether the target repository has a `scripts/` directory, whether the CWD is the user's project, or whether installation paths contain spaces.

