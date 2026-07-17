# Skills

Agent skills for AI coding assistants. This repository tracks reusable skills for diagramming, planning, auditing, codebase design, implementation, optimization, and GitHub issue planning.


## Install

Install individual skills with the `npx skills` CLI:

```bash
# Interactive menu — select the skills you want
npx skills add akshay-diwadkar/skills

# Or install individual skills by name
npx skills add akshay-diwadkar/skills --skill create-diagram
npx skills add akshay-diwadkar/skills --skill design-codebase-with-senior-dev
npx skills add akshay-diwadkar/skills --skill plan-with-senior-dev
npx skills add akshay-diwadkar/skills --skill codebase-issue-auditor
npx skills add akshay-diwadkar/skills --skill github-issue-planner
npx skills add akshay-diwadkar/skills --skill implement-with-senior-dev
npx skills add akshay-diwadkar/skills --skill optimize-codebase-with-senior-dev
```

Restart your agent after installing new skills.

Manual clone and symlink installation also works:

```bash
git clone https://github.com/akshay-diwadkar/skills.git
cd skills
mkdir -p ~/.agents/skills
ln -s "$PWD/create-diagram" ~/.agents/skills/
ln -s "$PWD/design-codebase-with-senior-dev" ~/.agents/skills/
ln -s "$PWD/plan-with-senior-dev" ~/.agents/skills/
ln -s "$PWD/codebase-issue-auditor" ~/.agents/skills/
ln -s "$PWD/github-issue-planner" ~/.agents/skills/
ln -s "$PWD/implement-with-senior-dev" ~/.agents/skills/
ln -s "$PWD/optimize-codebase-with-senior-dev" ~/.agents/skills/
```

## Skill Catalog

### `create-diagram`

Question-first diagram workflow for architecture maps, workflow visualizations, relationship graphs, and self-contained HTML artifacts. The skill explores the repo, asks only unresolved diagram questions, plans the output, builds through the bundled HTML template, validates the generated file, and verifies browser behavior.

### `design-codebase-with-senior-dev`

Evidence-driven architectural assessment and safe restructuring workflow. It determines whether a design change is justified, selects the smallest sufficient boundary or pattern, and defines or executes an incremental behavior-preserving migration. Unlike `codebase-issue-auditor`, it does not broadly discover issues; it starts from a scoped concern and identifies its structural cause and target design. Unlike `plan-with-senior-dev`, it decides architecture, ownership, dependency direction, pattern admission or removal, and migration shape rather than turning an approved design into a file/symbol-level implementation specification.

### `plan-with-senior-dev`

Planning-only workflow for repo-evidenced, decision-complete implementation specifications. The skill emphasizes local code evidence, smallest viable design, change propagation, constraint verification, concrete test strategy, and Devil's Advocate review before implementation.

### `codebase-issue-auditor`

Local repository audit workflow for evidence-backed bugs, risks, test gaps, architecture friction, performance issues, maintainability problems, and developer-experience improvements. Findings become GitHub issue drafts only after review; publishing is guarded by a dry run first and requires `--publish` for network writes.

### `github-issue-planner`

Fetches open non-PR GitHub issues, treats the local checkout as the implementation source of truth, and writes local Markdown resolution plans. GitHub is read-only by default. Branch creation, commits, pull requests, and post-merge follow-up happen only when the user explicitly opts into that lifecycle.

### `implement-with-senior-dev`

Safely implement an approved plan as a minimal patch. The skill treats the plan as a contract, preserves existing patterns, runs focused verification, and reports exactly what changed. Refuses vague plans instead of inventing missing behavior.

### `optimize-codebase-with-senior-dev`

Evidence-backed codebase optimization workflow with targeted and sweep modes. The skill deeply comprehends the repo, researches official documentation for underexploited capabilities, produces an ROI-ranked optimization ledger, and generates structured briefs for `plan-with-senior-dev`.

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