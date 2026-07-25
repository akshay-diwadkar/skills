# Installation Guide

This repository provides canonical engineering skills for AI coding environments. Follow the instructions below to install skills into your host environment.

---

## 1. skills.sh (Portable Skill CLI)

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
npx skills add akshay-diwadkar/skills --skill build-codebase-knowledge
```

### Updating & Removing

```bash
# Update skills
npx skills update

# Remove a skill
npx skills remove plan-with-senior-dev
```

---

## 2. Manual Clone & Symlink Installation

If your host environment does not support CLI installation, clone the repository and link individual skills manually into your agent skills folder (`~/.agents/skills`).

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
ln -s "$PWD/skills/engineering/build-codebase-knowledge" ~/.agents/skills/
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
New-Item -ItemType SymbolicLink -Path "$env:USERPROFILE\.agents\skills\build-codebase-knowledge" -Target "$PWD\skills\engineering\build-codebase-knowledge"
```

Restart your coding agent or IDE after installing or updating skills.

---

## 3. Installed-Runtime Script Execution Contract

Skills invoke bundled scripts (such as scaffolders, finalizers, and validators) during execution. When executing bundled runtime tools:

- **Deterministic Skill Root Contract**: Runtime commands execute with the active skill directory (the directory containing `SKILL.md`) set as the process working directory:
  ```bash
  python scripts/finalize_plan.py --tier <tier> --repo-root <repo-root> <draft>
  ```
- **Target Repository Isolation**: The target repository is specified explicitly via `--repo-root <repo-root>`. Tools inspect and modify target files independently without expecting scripts inside the target repository.
- **Claude Code Environment Variable**: On Claude Code, execution from an external directory may resolve the active skill root via `${CLAUDE_SKILL_DIR}`.
- **Internal Asset Resolution**: Bundled Python scripts locate internal contracts, assets, and templates relative to `Path(__file__).resolve().parent`. Commands execute cleanly regardless of whether the target repository has a `scripts/` directory, whether paths contain spaces, or whether installation is via symlinks.
