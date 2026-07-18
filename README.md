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

## Workflow

The skills form a composable engineering lifecycle. Start at the stage that matches your current problem, follow only the handoffs you need, and stop when you have the required artifact or verified change.

### Capability map

| Stage | Use when | Skill | Output and handoff |
|---|---|---|---|
| Discover | You need to find and prove codebase risks. | `codebase-issue-auditor` | Evidence-backed findings and reviewable issue drafts. Send an approved finding to optimization, design, or planning. |
| Discover | Open GitHub issues need actionable local plans. | `github-issue-planner` | One evidence-backed Markdown resolution plan per issue. Escalate only complex issues to senior planning. |
| Decide | You know the performance, tooling, or developer-experience goal. | `optimize-codebase-with-senior-dev` | A baseline, ROI-ranked optimization ledger, and structured brief for the highest-value change. |
| Decide | Boundaries, ownership, dependencies, or patterns may need to change. | `design-codebase-with-senior-dev` | A validated assessment, justified target design, and incremental behavior-preserving migration shape. This stage never edits implementation files. |
| Specify | An approved finding, brief, or target design needs exact implementation decisions. | `plan-with-senior-dev` | A decision-complete specification covering interfaces, logic, propagation, tests, and verification. |
| Communicate | Reviewers need a shared view of the current system, proposed design, or workflow. | `create-diagram` | A validated, self-contained HTML diagram for review or documentation. Use it before or after a design decision. |
| Deliver | A specific plan is approved and implementation is explicitly requested. | `implement-with-senior-dev` | A minimal, pattern-preserving patch with focused verification and an exact implementation report. |

The common path is **discover → decide → specify → deliver**. Diagramming can support any review point, and a targeted re-audit can verify residual risk after delivery. Neither step is mandatory.

### Recipe 1: Turn unknown risks into verified fixes

1. Run `codebase-issue-auditor` to build a coverage matrix and promote only reproducible findings.
2. Route an approved finding to `optimize-codebase-with-senior-dev` for capability or efficiency work, or to `design-codebase-with-senior-dev` for structural pressure.
3. Use `plan-with-senior-dev` to turn the chosen brief or target design into an executable specification.
4. Use `implement-with-senior-dev` to apply the smallest compliant patch and run focused verification.
5. Optionally re-run `codebase-issue-auditor` against the changed area to check for residual risks.

**Stop with:** a verified patch plus an evidence-backed view of any remaining risk.

### Recipe 2: Optimize a known bottleneck or developer workflow

1. Start with `optimize-codebase-with-senior-dev` to establish a baseline, research capabilities already available in the stack, and rank candidates by ROI.
2. If the best candidate changes architecture, use `design-codebase-with-senior-dev` to approve the smallest safe structural change. Otherwise, continue directly.
3. Hand the optimization brief or approved design to `plan-with-senior-dev`, then execute it with `implement-with-senior-dev`.
4. Compare the verified result with the original baseline. Stop if the success metric is met; return to the candidate ledger if it is not.

**Stop with:** a measured improvement, not merely a plausible optimization.

### Recipe 3: Redesign a critical subsystem safely

1. Use `design-codebase-with-senior-dev` to reconstruct the current design, test whether structural change is justified, and define reversible migration slices. The skill remains assessment-only.
2. Use `create-diagram` when reviewers need a shared current-state or target-state model before approving the design.
3. Convert the approved design into exact contracts, migration logic, rollback, and tests with `plan-with-senior-dev`.
4. Apply the slices with `implement-with-senior-dev`; optionally diagram the delivered design or run a targeted audit afterward.

**Stop with:** preserved behavior, an explicit migration record, and reviewable architecture documentation when needed.

### Recipe 4: Convert a GitHub backlog into implementation-ready work

1. Run `github-issue-planner` to fetch open non-PR issues and validate each one against the local checkout.
2. Use its local Markdown plan directly when the issue is decision-complete. Escalate to `plan-with-senior-dev` only when contracts, migrations, or cross-cutting behavior need deeper analysis.
3. Use `implement-with-senior-dev` for an approved plan. Branches, commits, pull requests, comments, and other GitHub writes remain opt-in.

**Stop with:** a locally verified implementation plan by default, or a verified patch and GitHub lifecycle only when explicitly requested.

## Skill Catalog

Skills are grouped by engineering workflow role.

### Audit & Analysis

#### `codebase-issue-auditor`

Audit a repository for evidence-backed bugs, risks, test gaps, architectural friction, performance hotspots, maintainability issues, and developer-experience optimizations, then draft GitHub issues for approval. Use when the user asks Codex to inspect a codebase, identify problems or criticalities, prioritize optimization work, or raise GitHub issues from audit findings.

#### `optimize-codebase-with-senior-dev`

Plan and, when explicitly requested, implement safe, evidence-backed codebase optimizations for runtime, frontend, backend, database, build, tests, CI/CD, dependencies, tooling, maintainability, architecture, and developer experience. Use after an approved audit finding, performance complaint, explicit optimization goal, DX pain, architecture concern, modernization target, or when asked to broadly discover optimization opportunities across a codebase. The skill deeply comprehends the repo, actively researches official framework and library documentation via web search to find underexploited capabilities, produces an ROI-ranked optimization ledger, and generates structured briefs for plan-with-senior-dev.

### Architecture & Design

#### `design-codebase-with-senior-dev`

Assess whether architectural change is justified, select the smallest evidence-backed codebase design, and define an incremental behavior-preserving migration. Use for boundary, dependency-direction, state-ownership, or subsystem redesign; design-pattern evaluation or removal; and safe structural restructuring. This skill never edits implementation files; approved designs move to planning and then implementation.

### Planning & Specification

#### `plan-with-senior-dev`

Plan code changes, refactors, bug fixes, migrations, public contracts, and risky integrations as repo-evidenced, decision-complete implementation specifications. Use when Codex must challenge assumptions, discover the real change boundary, compare repo-compatible approaches, specify exact interfaces and logic, trace success criteria through tests, or produce a one-shot plan that another engineer can implement without inventing behavior.

### Implementation

#### `implement-with-senior-dev`

Safely implement an approved, specific code-change plan as a minimal patch. Use when the user provides or points to an approved plan and wants Codex to implement it without scope expansion, preserve existing patterns, run focused verification, and report exactly what changed.

### Visualization

#### `create-diagram`

Diagram creation workflow for architecture diagrams, workflow visualizations, relationship graphs, self-contained HTML artifacts, and diagram requests that need clarifying questions before drawing.

### Workflow Integration

#### `github-issue-planner`

Fetch open GitHub issues, use the local checkout as the implementation source of truth, and write decision-complete local Markdown plans. Use when the user asks to plan GitHub issue fixes, prepare an implementation backlog from GitHub issues, inspect open issues before coding, produce read-only issue-resolution plans, or explicitly asks to execute ready issues through dedicated branches, commits, PRs, and post-merge follow-up.

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
ruff check plan-with-senior-dev/scripts create-diagram/scripts codebase-issue-auditor/scripts design-codebase-with-senior-dev/scripts github-issue-planner/scripts tests .github/scripts
mypy plan-with-senior-dev/scripts tests/plan-with-senior-dev
mypy codebase-issue-auditor/scripts tests/codebase-issue-auditor
mypy design-codebase-with-senior-dev/scripts tests/design-codebase-with-senior-dev
mypy github-issue-planner/scripts tests/github-issue-planner
mypy create-diagram/scripts tests/create-diagram
mypy .github/scripts tests/repository
python -m pytest -q
```

`design-codebase-with-senior-dev` also has an opt-in provider-neutral live evaluation runner. The adapter command reads one JSON request from stdin and writes one JSON response containing `assessment_markdown` to stdout. Model credentials and provider SDKs stay in the adapter, outside this repository.

```bash
python tests/design-codebase-with-senior-dev/run_live_evaluations.py \
  --adapter-command python path/to/adapter.py \
  --model-label weaker-model \
  --runs 3 \
  --output-dir .scratch/design-codebase-evals
```

The runner copies and hashes each fixture, treats mutations and adapter failures as hard failures, and requires a median score of 90 with no individual score below 80.

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
