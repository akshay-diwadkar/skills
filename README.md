# Skills

Agent skills for AI coding assistants. Skills are reusable, self-contained instructions that teach an agent to perform a specific task - planning, diagramming, debugging, issue auditing, etc.

## Structure

Each skill lives in a top-level directory and follows this convention:

```
skill-name/
  SKILL.md           # Required - frontmatter (name, description) + skill instructions
  references/        # Reference docs linked from SKILL.md
  scripts/           # Helper scripts (Python, shell, etc.)
  assets/            # Templates, static files
  agents/            # Sub-agent configs (e.g., openai.yaml)
```

## Installation

Use the `npx skills` CLI to install individual skills from this repo:

```bash
npx skills add akshay-diwadkar/skills --skill create-diagram
npx skills add akshay-diwadkar/skills --skill plan-with-senior-dev
npx skills add akshay-diwadkar/skills --skill codebase-issue-auditor
npx skills add akshay-diwadkar/skills --skill github-issue-planner
```

Restart your agent after installing new skills.

Manual clone and symlink installation also works:

```bash
git clone https://github.com/akshay-diwadkar/skills.git
cd skills

# Symlink individual skills into your agent's skills directory
mkdir -p ~/.agents/skills
ln -s "$PWD/create-diagram" ~/.agents/skills/
ln -s "$PWD/plan-with-senior-dev" ~/.agents/skills/
ln -s "$PWD/codebase-issue-auditor" ~/.agents/skills/
ln -s "$PWD/github-issue-planner" ~/.agents/skills/

# Or copy instead of symlink:
# cp -r create-diagram ~/.agents/skills/
# cp -r plan-with-senior-dev ~/.agents/skills/
# cp -r codebase-issue-auditor ~/.agents/skills/
# cp -r github-issue-planner ~/.agents/skills/
```

## Usage

Skills in `~/.agents/skills/` are auto-discovered by the agent. To use a skill:

1. **By name** - the agent loads the skill automatically when the task matches its description
2. **By trigger** - skills with a `triggers` field in their frontmatter activate on matching phrases (e.g., `/graphify`)
3. **Manually** - reference a skill in your agent config file (e.g., `opencode.json` or `CLAUDE.md`) under the skills section

## Tracked Skills

### Planning & Design

- **plan-with-senior-dev** - Produce codebase-grounded, decision-complete implementation plans through focused exploration, plan-shaping questions, existing-pattern alignment, domain-doc judgment, and concrete verification. Run `scripts/check_plan_shape.py` and `scripts/check_plan_rubric.py` to validate plan quality.
- **github-issue-planner** - Fetch open GitHub issues for a repository, read issue bodies and comments, inspect the local codebase, and write decision-complete implementation plans to a local Markdown report. GitHub is read-only for this skill.

### Auditing & Issue Publishing

- **codebase-issue-auditor** - Audit a local repository for evidence-backed bugs, risks, test gaps, architectural friction, performance hotspots, maintainability issues, and developer-experience optimizations, then draft GitHub issues for approval. Publishing requires an explicit dry run first and `--publish` for network writes.

### Communication & Diagramming

- **create-diagram** - Grilling workflow that questions the user to shared understanding, then produces an Excalidraw-style HTML diagram. Use for architecture maps, relationship graphs, workflow visualizations, or any diagram that benefits from clarifying questions first.

## GitHub Token Setup

`codebase-issue-auditor` and `github-issue-planner` use a GitHub token for repository issue access. `GITHUB_TOKEN` is required. Skill-specific `.env.example` files are safe to track; real `.env` files contain secrets and must stay local.

### Option 1: `.env` file

Copy the matching template inside the skill directory:

```bash
cp codebase-issue-auditor/.env.example codebase-issue-auditor/.env
cp github-issue-planner/.env.example github-issue-planner/.env
```

Fill in `GITHUB_TOKEN`, then pass the file to the bundled scripts:

```bash
python codebase-issue-auditor/scripts/check_github_env.py --env codebase-issue-auditor/.env
python github-issue-planner/scripts/check_github_env.py --env github-issue-planner/.env --github-repo-url https://github.com/owner/repo
```

### Option 2: shell environment

PowerShell:

```powershell
.\codebase-issue-auditor\scripts\load_github_env.ps1 -EnvPath .\codebase-issue-auditor\.env
$env:GITHUB_TOKEN = "your_token_here"
```

Bash or zsh:

```bash
source codebase-issue-auditor/scripts/load_github_env.sh codebase-issue-auditor/.env
export GITHUB_TOKEN=your_token_here
```

The planner scripts also accept already-exported `GITHUB_TOKEN` values. Use `--github-repo-url` for the target repository rather than storing the destination in `.env`.

### Secret Handling

- Commit `.env.example`; never commit a real `.env`.
- Do not print, `cat`, `Get-Content`, `type`, `rg`, or otherwise inspect real `.env` contents in agent context.
- Use the bundled checker scripts to validate configuration because they mask token values.
- Treat generated issue payloads such as root `issues.json` as local output unless intentionally reviewed and added elsewhere.

## Tracking Policy

The `.gitignore` ignores everything by default and explicitly un-ignores the tracked skill source for `create-diagram/`, `plan-with-senior-dev/`, `codebase-issue-auditor/`, and `github-issue-planner/`. Real `.env` files, generated payloads such as root `issues.json`, caches, and other local skills remain outside version control.
