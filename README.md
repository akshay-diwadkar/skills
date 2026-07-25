# Engineering Skills

[![Repository Quality](https://github.com/akshay-diwadkar/skills/actions/workflows/quality.yml/badge.svg?branch=main)](https://github.com/akshay-diwadkar/skills/actions/workflows/quality.yml)
[![Release](https://img.shields.io/github/v/release/akshay-diwadkar/skills?label=Release)](https://github.com/akshay-diwadkar/skills/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](pyproject.toml)
[![skills.sh Compatible](https://img.shields.io/badge/skills.sh-Supported-black.svg)](docs/compatibility.md)

A production-grade engineering skill monorepo for AI coding agents and human engineers. It provides validated skills for auditing, architecture, planning, implementation, optimization, issue resolution, and system diagramming.

Workflows are repository-grounded, safety-conscious, and backed by automated repository contract checks.

---

## Why Use It

Unlike generic system prompts or simple snippet collections, these engineering skills provide structured, contract-backed workflows:

- **Repository-Grounded Analysis**: Skills inspect your actual source code, test suites, and git state rather than offering unverified advice.
- **Strict Execution Contracts**: Planning, architecture, optimization, and implementation workflows enforce explicit contracts and output verification.
- **Explicit Authorization**: Destructive operations, repository modifications, and external actions require explicit confirmation.
- **Validator-Backed Claims**: Completion claims require passing automated verification checks and gathering empirical proof.

---

## Included Skills

<!-- BEGIN GENERATED SKILL CATALOG -->
| Skill | Domain | Kind | Status | Invocation | Summary |
| --- | --- | --- | --- | --- | --- |
| [plan-with-senior-dev](docs/skills/plan-with-senior-dev.md) | `engineering` | `workflow` | `stable` | `both` | Turn a feature, bug fix, refactor, migration, public contract, or risky integration into a repository-grounded, decision-complete implementation blueprint. |
| [implement-with-senior-dev](docs/skills/implement-with-senior-dev.md) | `engineering` | `workflow` | `stable` | `both` | Execute an approved implementation plan as the smallest complete patch — preserving existing patterns and uncommitted work, with layered verification and an exact change report. |
| [github-issue-planner](docs/skills/github-issue-planner.md) | `engineering` | `workflow` | `stable` | `both` | Turn GitHub issues into implementation plans. Inventory open issues, then plan one selected issue against the local checkout, treating issue text as untrusted claims. |
| [codebase-issue-auditor](docs/skills/codebase-issue-auditor.md) | `engineering` | `workflow` | `stable` | `both` | Audit a repository for bugs, security and performance risks, test gaps, and architectural or maintainability friction, and draft GitHub issues from confirmed findings. |
| [create-diagram](docs/skills/create-diagram.md) | `engineering` | `workflow` | `stable` | `both` | Create self-contained HTML diagrams of systems, architectures, workflows, and code relationships. |
| [design-codebase-with-senior-dev](docs/skills/design-codebase-with-senior-dev.md) | `engineering` | `discipline` | `stable` | `both` | Assess whether architectural change is justified and choose the smallest evidence-backed design, with an incremental behavior-preserving migration path. |
| [optimize-codebase-with-senior-dev](docs/skills/optimize-codebase-with-senior-dev.md) | `engineering` | `discipline` | `stable` | `both` | Optimize a named bottleneck, workflow, or tooling pain with evidence-backed changes that preserve behavior — planning first, implementation only on explicit request. |
| [build-codebase-knowledge](docs/skills/build-codebase-knowledge.md) | `engineering` | `utility` | `stable` | `both` | Generate and maintain a compact repository-intelligence layer and task resolver to minimize broad exploration, token consumption, and context usage. |
<!-- END GENERATED SKILL CATALOG -->

### Skill Lifecycle Roles

- **Discover**: `codebase-issue-auditor`, `github-issue-planner`
- **Decide**: `design-codebase-with-senior-dev`, `optimize-codebase-with-senior-dev`
- **Specify**: `plan-with-senior-dev`
- **Deliver**: `implement-with-senior-dev`
- **Communicate**: `create-diagram`
- **Intelligence Layer**: `build-codebase-knowledge`

---

## Installation & Usage

### 1. Portable Skill CLI (`skills.sh`)

To install individual skills using the portable CLI:

```bash
# Interactive skill selection
npx skills add akshay-diwadkar/skills

# Install a specific skill
npx skills add akshay-diwadkar/skills --skill plan-with-senior-dev
```

### 2. Manual Clone & Symlinks

For local development or agent integration:

```bash
# Linux / macOS
git clone https://github.com/akshay-diwadkar/skills.git
mkdir -p ~/.agents/skills
ln -s "$PWD/skills/engineering/plan-with-senior-dev" ~/.agents/skills/
```

```powershell
# Windows PowerShell
git clone https://github.com/akshay-diwadkar/skills.git
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.agents\skills"
New-Item -ItemType SymbolicLink -Path "$env:USERPROFILE\.agents\skills\plan-with-senior-dev" -Target "$PWD\skills\engineering\plan-with-senior-dev"
```

For detailed options, see [Installation Guide](docs/installation.md).

---

## Safety Model & Controls

All workflows enforce explicit safety boundaries:

- **Repository Evidence**: Analysis must be grounded in actual codebase inspection.
- **Read-Only Gating**: Planning, design, and audit skills never edit project source code without explicit request.
- **Explicit Write Authorization**: Source code mutations require explicit user confirmation.
- **Dirty Worktree Protection**: Uncommitted local user changes are protected and preserved during execution.
- **Executable Verification**: Implementation completion requires passing verification commands and gathering empirical proof.

For details, see [Safety & Controls](docs/safety.md).

---

## Documentation Index

Explore detailed documentation under `docs/`:

- [Getting Started](docs/getting-started.md) — Core concepts, skill selection, and first steps.
- [Installation](docs/installation.md) — Complete setup guides for skills.sh and manual symlinks.
- [Workflow Lifecycle](docs/workflow.md) — Lifecycle stages, handoffs, and operational recipes.
- [Platform Compatibility](docs/compatibility.md) — Discovery mechanisms and support claims.
- [Repository Architecture](docs/architecture.md) — Monorepo design, catalog ownership, and directory structure.
- [Safety & Controls](docs/safety.md) — Access permissions, execution gates, and policy rules.
- [Testing & Verification](docs/testing.md) — Multi-layer test strategy and contract validation.
- [Live Model Evaluations](docs/evaluations.md) — Provider-neutral eval runners, fixtures, and failure rules.
- [Authoring Skills](docs/authoring-skills.md) — Step-by-step guide to authoring new skills.
- [Release Process](docs/release-process.md) — Maintainer pre-release protocol and packaging verification.
- [Contributing Guide](docs/contributing.md) — Development guidelines and pull request standards.

---

## Maintainer Verification

When working in the source repository checkout, maintainers run the following validation sweep before submitting PRs or tagging releases:

```bash
python tools/validation/validate_repository.py
python tools/packaging/verify_distribution.py
python -m pytest -q
```

---

## Contributing, Security & License

- [Contributing Guide](CONTRIBUTING.md) / [Deep Guide](docs/contributing.md)
- [Security Policy](SECURITY.md)
- [License (MIT)](LICENSE)
- [Changelog](CHANGELOG.md)
