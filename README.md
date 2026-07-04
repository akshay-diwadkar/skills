# Skills

Agent skills for AI coding assistants. This repository tracks a small set of reusable skills for diagramming, planning, auditing, and GitHub issue planning.


## Install

Install individual skills with the `npx skills` CLI:

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
mkdir -p ~/.agents/skills
ln -s "$PWD/create-diagram" ~/.agents/skills/
ln -s "$PWD/plan-with-senior-dev" ~/.agents/skills/
ln -s "$PWD/codebase-issue-auditor" ~/.agents/skills/
ln -s "$PWD/github-issue-planner" ~/.agents/skills/
```

## Skill Catalog

### `create-diagram`

Question-first diagram workflow for architecture maps, workflow visualizations, relationship graphs, and self-contained HTML artifacts. The skill explores the repo, asks only unresolved diagram questions, plans the output, builds through the bundled HTML template, validates the generated file, and verifies browser behavior.

### `plan-with-senior-dev`

Planning-only workflow for repo-evidenced, decision-complete implementation specifications. The skill emphasizes local code evidence, smallest viable design, change propagation, constraint verification, concrete test strategy, and Devil's Advocate review before implementation.

### `codebase-issue-auditor`

Local repository audit workflow for evidence-backed bugs, risks, test gaps, architecture friction, performance issues, maintainability problems, and developer-experience improvements. Findings become GitHub issue drafts only after review; publishing is guarded by a dry run first and requires `--publish` for network writes.

### `github-issue-planner`

Fetches open non-PR GitHub issues, treats the local checkout as the implementation source of truth, and writes local Markdown resolution plans. GitHub is read-only by default. Branch creation, commits, pull requests, and post-merge follow-up happen only when the user explicitly opts into that lifecycle.

## GitHub Setup

`codebase-issue-auditor` and `github-issue-planner` authenticate through the GitHub CLI:

```bash
gh auth login
```

Use the bundled checker scripts to validate local configuration without exposing secrets:

```bash
python codebase-issue-auditor/scripts/check_github_env.py --github-repo-url owner/repo
python github-issue-planner/scripts/check_github_env.py --github-repo-url owner/repo
```

Optional `.env` files may be used for non-secret defaults.

For `codebase-issue-auditor`:

```dotenv
GITHUB_DEFAULT_LABELS=audit,needs-triage
GITHUB_SKIP_DUPLICATES=true
```

For `github-issue-planner`:

```dotenv
GITHUB_ISSUE_FETCH_LABELS=
GITHUB_ISSUE_FETCH_LIMIT=
GITHUB_API_URL=
```

Commit `.env.example` files only. Real `.env` files must stay local and must not be committed.

## Maintainer Checks

CI runs repository quality checks on Python 3.11:

```bash
python .github/scripts/validate_skill_tree.py
ruff check plan-with-senior-dev/scripts create-diagram/scripts create-diagram/test codebase-issue-auditor/scripts github-issue-planner/scripts .github/scripts
mypy plan-with-senior-dev/scripts
mypy codebase-issue-auditor/scripts
mypy github-issue-planner/scripts
mypy create-diagram/scripts create-diagram/test
mypy .github/scripts
python -m pytest -q
```

CI also runs `create-diagram` checks across Windows, macOS, and Linux on Python 3.9 through 3.12:

```bash
python -m unittest discover -s create-diagram/test -v
python create-diagram/scripts/check_template_refs.py
python create-diagram/scripts/build_diagram.py --data create-diagram/test/fixtures/complex.json --output create-diagram-smoke.html --overwrite
python create-diagram/scripts/validate_diagram.py create-diagram-smoke.html
```

The optional browser smoke check requires Playwright:

```bash
python -m pip install playwright
python -m playwright install chromium
python create-diagram/scripts/browser_smoke.py
```

## Tracking Policy

The `.gitignore` ignores everything by default, then explicitly un-ignores this README, `pyproject.toml`, CI workflow files, and the four tracked skill folders. Generated payloads, caches, real `.env` files, root issue output such as `issues.json`, and unrelated local skills remain outside version control.
