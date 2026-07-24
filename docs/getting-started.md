# Getting Started

Welcome to the **Engineering Skills** plugin. This project provides role-based AI engineering agents and validated engineering skills for software development.

## Core Interaction Model: Agents vs. Skills

This monorepo supports two primary interaction styles:

1. **Role-Based Agents (Recommended)**: Higher-level AI personas tailored for specific engineering disciplines (e.g. Architecture, Delivery, Issue Resolution, Health & Optimization). Agents automatically select and coordinate underlying skills to perform complex, multi-step workflows.
2. **Direct Skill Invocation (Advanced / Focused)**: Specific, single-purpose workflow or discipline instructions (e.g. `plan-with-senior-dev`, `implement-with-senior-dev`, `create-diagram`). You can invoke individual skills directly when you need a single, isolated operation without agent orchestration.

## Quick Installation

- **Claude Code Marketplace**: `/plugin install engineering-skills@engineering-skills-marketplace`
- **Cursor Local Plugin**: Symlink or copy to `~/.cursor/plugins/local/engineering-skills`
- **Codex Project Installer**: Run `python tools/agents/install_codex_agents.py --target <target-project> --write`

For complete platform installation options, see [Installation Guide](installation.md).

## Recommended First Interaction

When using a supported agent host (such as Claude Code, Cursor, or Codex), start by addressing your request to the appropriate role agent or asking the assistant to take on that role.

### Example Prompts

- **Audit & Discovery**:
  > "Take on the codebase-health-engineer role and audit this repository for critical defects, security risks, and test gaps."

- **Architecture Review**:
  > "Act as the architecture-engineer and evaluate whether refactoring the data access layer in this repository is actually justified."

- **Feature Delivery**:
  > "Act as the delivery-engineer: plan the implementation of a new rate-limiting middleware, then wait for my approval before modifying files."

- **GitHub Issue Resolution**:
  > "Use issue-resolution-engineer to inspect open GitHub issues, select the highest-priority bug, and draft an executable plan."

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

At any stage, you can request an architecture or workflow diagram (`create-diagram`).

## Safety and Authorization Model

All workflows in this plugin adhere to strict safety boundaries:

- **No Blind Recommendations**: Analyses require empirical codebase evidence.
- **Planning-Only Gating**: Planning, design, and audit skills never edit project source code.
- **Explicit Authorization**: Destructive operations, source code writes, and external network actions require explicit user confirmation.
- **Dirty Worktree Protection**: Uncommitted local user changes are protected and preserved during implementation execution.
- **Executable Verification**: Implementation completion requires running verification commands and gathering empirical proof.

For more details on safety guarantees, see [Safety & Controls](safety.md).
