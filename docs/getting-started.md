# Getting Started

Welcome to **Engineering Skills**. This project provides validated engineering skills for software development.

## Core Interaction Model

This monorepo provides canonical engineering skills (e.g. `plan-with-senior-dev`, `implement-with-senior-dev`, `create-diagram`, `build-codebase-knowledge`). You can invoke individual skills directly when you need a structured, contract-backed engineering operation.

## Quick Installation

- **skills.sh CLI**: `npx skills add akshay-diwadkar/skills --skill plan-with-senior-dev`
- **Manual Clone / Symlink**: Clone the repo and symlink desired skills into your agent skills directory (`~/.agents/skills/`).

For complete installation options, see [Installation Guide](installation.md).

## Recommended First Interaction

Start by asking your AI assistant to use one of the canonical skills for your task:

### Example Prompts

- **Audit & Discovery**:
  > "Use codebase-issue-auditor to inspect this repository for critical defects, security risks, and test gaps."

- **Architecture Review**:
  > "Use design-codebase-with-senior-dev to evaluate whether refactoring the data access layer in this repository is actually justified."

- **Feature Specification**:
  > "Use plan-with-senior-dev to plan the implementation of a new rate-limiting middleware, then wait for my approval before modifying files."

- **Feature Implementation**:
  > "Use implement-with-senior-dev to execute the approved plan."

## Workflow Lifecycle & Entry Points

Engineering tasks typically progress through four lifecycle stages:

```
Discover ──> Decide ──> Specify ──> Deliver
```

You can enter the workflow at whichever stage matches your current state:

- **Discover**: Start here if you have an unfamiliar repository (`codebase-issue-auditor`) or an unverified GitHub issue (`github-issue-planner`).
- **Decide**: Start here if you suspect architectural debt (`design-codebase-with-senior-dev`) or have a slow/clunky workflow (`optimize-codebase-with-senior-dev`).
- **Specify**: Start here if you already know what feature or bug fix you want and need a decision-complete plan (`plan-with-senior-dev`).
- **Deliver**: Start here if you have an approved implementation blueprint and need to execute code changes safely (`implement-with-senior-dev`).
- **Intelligence**: Use `build-codebase-knowledge` to build/maintain repository context and resolve tasks with minimum token usage.

At any stage, you can request an architecture or workflow diagram (`create-diagram`).

## Safety and Authorization Model

All skills in this monorepo adhere to strict safety boundaries:

- **No Blind Recommendations**: Analyses require empirical codebase evidence.
- **Planning-Only Gating**: Planning, design, and audit skills never edit project source code.
- **Explicit Authorization**: Destructive operations and source code writes require explicit user confirmation.
- **Dirty Worktree Protection**: Uncommitted local user changes are protected and preserved during implementation execution.
- **Executable Verification**: Implementation completion requires running verification commands and gathering empirical proof.

For more details on safety guarantees, see [Safety & Controls](safety.md).
