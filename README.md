# Skills

Agent skills for AI coding assistants — one skill per stage of the engineering lifecycle: audit, issue planning, optimization, design, specification, implementation, and diagramming.


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

## Workflow

Seven skills, one lifecycle: find what's wrong, decide what to do about it, specify the change exactly, then make it. Start at the stage that matches your problem and follow only the handoffs you need.

### Capability map

| Stage | You have | Skill | You get |
|---|---|---|---|
| Discover | A repo you don't trust yet | `codebase-issue-auditor` | Evidence-backed findings; GitHub issue drafts on approval |
| Discover | Open GitHub issues | `github-issue-planner` | One issue planned against your checkout |
| Decide | A slow or clunky workflow | `optimize-codebase-with-senior-dev` | A baseline, ranked options, and a brief for the best one |
| Decide | A design that feels wrong | `design-codebase-with-senior-dev` | A verdict on whether restructuring is worth it, plus the smallest safe migration |
| Specify | A change you can describe | `plan-with-senior-dev` | A decision-complete spec: interfaces, logic, tests, rollback |
| Communicate | A system nobody can picture | `create-diagram` | A self-contained HTML diagram grounded in the repo |
| Deliver | An approved plan | `implement-with-senior-dev` | The smallest satisfying patch, verified and reported |

The common path is **discover → decide → specify → deliver**. Diagramming supports any review point, and a targeted re-audit after delivery checks residual risk. Neither is mandatory.

### Recipe 1: Turn unknown risks into verified fixes

1. Run `codebase-issue-auditor` and promote only reproducible findings.
2. Route an approved finding to `optimize-codebase-with-senior-dev` for efficiency work, or to `design-codebase-with-senior-dev` for structural pressure.
3. Use `plan-with-senior-dev` to turn the chosen brief or design into an executable spec.
4. Use `implement-with-senior-dev` to apply the patch and verify it.
5. Optionally re-audit the changed area for residual risk.

**Stop with:** a verified patch and an honest view of what's still risky.

### Recipe 2: Optimize a known bottleneck or workflow

1. Start with `optimize-codebase-with-senior-dev`: baseline the workflow, research what the stack already gives you, rank the candidates.
2. If the winner requires restructuring, approve the design with `design-codebase-with-senior-dev` first. Otherwise skip ahead.
3. Hand the brief or approved design to `plan-with-senior-dev`, then execute with `implement-with-senior-dev`.
4. Compare the result with the baseline. Met the metric? Stop. Missed it? Back to the candidate list.

**Stop with:** a measured improvement, not a plausible one.

### Recipe 3: Redesign a critical subsystem safely

1. Use `design-codebase-with-senior-dev` to reconstruct the current design, test whether change is justified, and define reversible migration slices. It never edits code.
2. Use `create-diagram` when reviewers need a shared picture of current or target state before approving.
3. Turn the approved design into contracts, migration logic, rollback, and tests with `plan-with-senior-dev`.
4. Apply the slices with `implement-with-senior-dev`. Diagram the result or re-audit afterward if useful.

**Stop with:** preserved behavior and a migration record you can review.

### Recipe 4: Convert a GitHub backlog into implementation-ready work

1. Run `github-issue-planner` to inventory open issues and plan one against your checkout.
2. Simple issues yield a ready-to-implement plan directly. Anything touching public contracts, migrations, security, concurrency, or multiple subsystems routes into `plan-with-senior-dev`.
3. Execute an approved plan with `implement-with-senior-dev`. Branch, PR, and post-merge steps stay opt-in.

**Stop with:** a local plan by default — a verified patch and GitHub lifecycle only when you ask.

## Skill Catalog

Skills are grouped by engineering workflow role.

### Audit & Analysis

#### `codebase-issue-auditor`

Audit a repository for bugs, security and performance risks, test gaps, and architectural or maintainability friction, and draft GitHub issues from confirmed findings. Use when asked to inspect a codebase for problems, review overall code quality, hunt for unknown risks, or verify whether prior audit findings were resolved.

#### `optimize-codebase-with-senior-dev`

Optimize a named bottleneck, workflow, or tooling pain with evidence-backed changes that preserve behavior — planning first, implementation only on explicit request. Also runs repository-wide optimization sweeps when asked. Use for performance, build, CI, dependency, or developer-experience targets; for finding unknown problems, use codebase-issue-auditor.

### Architecture & Design

#### `design-codebase-with-senior-dev`

Assess whether architectural change is justified and choose the smallest evidence-backed design, with an incremental behavior-preserving migration path. Use for boundary, dependency-direction, or state-ownership redesign, design-pattern evaluation or removal, and subsystem restructuring. Assessment-only — produces no code; route approved designs to plan-with-senior-dev.

### Planning & Specification

#### `plan-with-senior-dev`

Turn a requested change — feature, bug fix, refactor, migration, public contract, or risky integration — into a decision-complete implementation plan that another engineer can execute without inventing behavior. Use when the user asks to plan, spec, or think through a code change before writing it. Planning-only; produces no code.

### Implementation

#### `implement-with-senior-dev`

Execute an approved implementation plan as the smallest complete patch — preserving existing patterns and uncommitted work, with layered verification and an exact change report. Use when the user has an approved or written plan and asks to implement, apply, or build it. Vague plans are refused back to planning.

### Visualization

#### `create-diagram`

Create self-contained HTML diagrams of systems, architectures, workflows, and code relationships. Use when the user asks for a diagram, an architecture picture, or a workflow visualization, or wants to communicate a design visually.

### Workflow Integration

#### `github-issue-planner`

Turn GitHub issues into implementation plans. Inventory open issues, then plan one selected issue against the local checkout, treating issue text as untrusted claims. Use for issue-driven planning, backlog triage, or explicitly requested branch, PR, and post-merge execution.

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
```

The issue planner targets GitHub.com through the authenticated `gh` CLI. Legacy empty or `https://api.github.com` API values are accepted, but custom API endpoints fail preflight.

Commit `.env.example` files only. Real `.env` files must stay local and must not be committed.

## Maintainer Checks

CI runs repository quality checks on Python 3.11:

```bash
python .github/scripts/validate_skill_tree.py
ruff check plan-with-senior-dev/scripts create-diagram/scripts codebase-issue-auditor/scripts design-codebase-with-senior-dev/scripts github-issue-planner/scripts implement-with-senior-dev/scripts optimize-codebase-with-senior-dev/scripts tests .github/scripts
mypy plan-with-senior-dev/scripts tests/plan-with-senior-dev
mypy codebase-issue-auditor/scripts tests/codebase-issue-auditor
mypy design-codebase-with-senior-dev/scripts tests/design-codebase-with-senior-dev
mypy optimize-codebase-with-senior-dev/scripts tests/optimize-codebase-with-senior-dev
mypy github-issue-planner/scripts tests/github-issue-planner
mypy create-diagram/scripts tests/create-diagram
mypy implement-with-senior-dev/scripts tests/implement-with-senior-dev
mypy .github/scripts tests/repository
python -m pytest -q
```

`implement-with-senior-dev` uses an executable run contract. Store the plan snapshot and bundle in a Git-ignored scratch path or an OS temporary directory:

```bash
python implement-with-senior-dev/scripts/scaffold_implementation.py \
  --repo-root /path/to/repo \
  --plan /ignored/run/plan.md \
  --output /ignored/run/implementation.json
python implement-with-senior-dev/scripts/finalize_implementation.py \
  --repo-root /path/to/repo \
  --plan /ignored/run/plan.md \
  /ignored/run/implementation.json
```

Its provider-neutral live adapter reads one JSON request from stdin with `repo_root`, `skill_path`, `plan_path`, and `run_bundle_path`. It may mutate only the disposable repository copy and returns JSON containing `implementation_report_markdown`:

```bash
python tests/implement-with-senior-dev/run_live_evaluations.py \
  --adapter-command python path/to/adapter.py \
  --model-label weaker-model \
  --runs 3 \
  --output-dir .scratch/implement-with-senior-dev-evals
```

The runner checks actual diffs, preserved dirty sentinels, authoritative verification commands, the implementation bundle, and report truthfulness. Passing requires no hard failures, a median score of at least 90, and every run at least 80. Without a configured adapter and completed run, weaker-model reliability remains unverified.

`design-codebase-with-senior-dev` also has an opt-in provider-neutral live evaluation runner. The adapter command reads one JSON request from stdin and writes one JSON response containing `assessment_markdown` to stdout. Model credentials and provider SDKs stay in the adapter, outside this repository.

```bash
python tests/design-codebase-with-senior-dev/run_live_evaluations.py \
  --adapter-command python path/to/adapter.py \
  --model-label weaker-model \
  --runs 3 \
  --output-dir .scratch/design-codebase-evals
```

The runner copies and hashes each fixture, treats mutations and adapter failures as hard failures, and requires a median score of 90 with no individual score below 80.

`optimize-codebase-with-senior-dev` uses an executable report contract. Generate and validate reports from the skill directory:

```bash
python scripts/scaffold_optimization.py --scope targeted --stage plan > optimization.md
python scripts/check_optimization.py --scope targeted --stage plan --repo-root /path/to/repo optimization.md
```

Its provider-neutral live evaluation adapter reads one JSON request from stdin and writes one JSON response containing `optimization_markdown` to stdout:

```bash
python tests/optimize-codebase-with-senior-dev/run_live_evaluations.py \
  --adapter-command python path/to/adapter.py \
  --model-label weaker-model \
  --runs 3 \
  --output-dir .scratch/optimize-codebase-evals
```

The runner hashes copied fixtures, treats mutation and adapter failures as hard failures, and requires a median score of 90 with every run at least 80. Without a configured adapter, weaker-model reliability remains unverified.

CI also runs `create-diagram` checks across Windows, macOS, and Linux on Python 3.9 through 3.12:

```bash
python -m unittest discover -s tests/create-diagram -v
python tests/create-diagram/check_template_refs.py
python create-diagram/scripts/build_diagram.py --data tests/create-diagram/fixtures/complex.json --output create-diagram-smoke.html --overwrite
python create-diagram/scripts/validate_diagram.py create-diagram-smoke.html
```

The optional browser smoke check requires Playwright:

```bash
python -m pip install playwright
python -m playwright install chromium
python tests/create-diagram/browser_smoke.py
```
