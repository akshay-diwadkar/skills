# Engineering Lifecycle & Workflow Handoffs

This repository provides a unified 4-stage engineering lifecycle: **Discover → Decide → Specify → Deliver**.

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│    Discover     │  ───> │     Decide      │  ───> │     Specify     │  ───> │     Deliver     │
│                 │       │                 │       │                 │       │                 │
│ • Auditor       │       │ • Architecture  │       │ • Plan with     │       │ • Implement     │
│ • Issue Planner │       │ • Optimization  │       │   Senior Dev    │       │   Senior Dev    │
└─────────────────┘       └─────────────────┘       └─────────────────┘       └─────────────────┘
        │                         │                         │                         │
        └─────────────────────────┼─────────────────────────┴─────────────────────────┘
                                  ▼
                         ┌─────────────────┐
                         │ Visualize / HTML│
                         │ Create Diagram  │
                         └─────────────────┘
```

---

## 1. Lifecycle Stages

### Stage 1: Discover
Find issues, analyze risk, and inventory requirements without altering source code.
- **Skills**: `codebase-issue-auditor`, `github-issue-planner`
- **Output**: Evidence-backed defect lists, approved issue drafts, or single-issue implementation briefs.

### Stage 2: Decide
Evaluate architectural changes or performance optimizations before committing to implementation.
- **Skills**: `design-codebase-with-senior-dev`, `optimize-codebase-with-senior-dev`
- **Output**: Reversible migration designs, architectural verdicts, or baseline optimization briefs.

### Stage 3: Specify
Formulate decision-complete specifications, interface contracts, logic requirements, and verification commands.
- **Skills**: `plan-with-senior-dev`
- **Output**: Contract-v3 validated Markdown specification blueprint.

### Stage 4: Deliver
Apply an approved plan as a minimal complete patch with verification proof.
- **Skills**: `implement-with-senior-dev`
- **Output**: Verified source code changes and change report.

### Stage 5 (Cross-cutting): Communicate & Visualize
Visualize systems, component relationships, state machines, or workflow boundaries at any stage.
- **Skills**: `create-diagram`
- **Output**: Self-contained HTML diagrams rendered in-browser.

---

## 2. Standard Recipes & Handoffs

### Recipe 1: Unknown Risks to Verified Fixes
1. Run `codebase-issue-auditor` to identify reproducible bugs, security flaws, or test gaps.
2. Route structural findings to `design-codebase-with-senior-dev` or performance issues to `optimize-codebase-with-senior-dev`.
3. Specify the change using `plan-with-senior-dev`.
4. Execute and verify the patch with `implement-with-senior-dev`.
5. Optionally re-audit the changed subsystem to ensure zero residual risk.

### Recipe 2: Safe Architectural Refactoring
1. Reconstruct current architecture and evaluate restructuring justification using `design-codebase-with-senior-dev`.
2. Generate a visual architecture diagram with `create-diagram` for reviewer alignment.
3. Turn approved migration steps into contract specifications with `plan-with-senior-dev`.
4. Apply migration slices incrementally with `implement-with-senior-dev`.

### Recipe 3: GitHub Issue Triage to Delivery
1. Run `github-issue-planner` to inventory open GitHub issues and reconcile claims against local source code.
2. Produce a ready-to-implement specification blueprint directly for straightforward fixes, or route to `plan-with-senior-dev` for complex/multi-system changes.
3. Apply changes with `implement-with-senior-dev`.

---

## 3. Optional Handoffs & Custom Entry Points

You do not need to execute all four stages sequentially for every task:

- **Direct Implementation**: If a comprehensive plan already exists, skip directly to `implement-with-senior-dev`.
- **Standalone Diagramming**: Ask `create-diagram` to visualize any existing codebase area without invoking planning or audit skills.
- **Assessment Only**: Use `design-codebase-with-senior-dev` to answer "Is refactoring worth it?" without generating code or implementation plans.
