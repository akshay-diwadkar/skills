---
name: implement-with-senior-dev
description: Safely implement an approved, specific code-change plan as a minimal patch. Use when the user provides or points to an approved plan and wants Codex to implement it without scope expansion, preserve existing patterns, run focused verification, and report exactly what changed.
---

# Implement With Senior Dev

Implement only the approved plan in front of you. Treat the plan as a contract, not a suggestion queue.

## Contract

Always:

- Read the plan first and identify the plan source before editing.
- Refuse vague plans instead of inventing missing behavior.
- Preserve existing patterns, naming, architecture, error handling, and test style.
- Make the smallest patch that satisfies the plan.
- Run focused verification that proves the planned behavior.
- Report exactly what changed, what ran, and what remains.

Never:

- Expand scope beyond the plan.
- Silently improve unrelated files, style, naming, tests, docs, or architecture.
- Rewrite broad areas when a local edit satisfies the plan.
- Overwrite user changes or clean a dirty worktree unless explicitly asked.
- Continue implementation after discovering a contradiction between the plan and repo reality.

## Gates

### 1. Plan Gate

Read the plan completely. Extract the goal, success criteria, in-scope files or behavior, out-of-scope boundaries, expected user-visible behavior, and verification commands or scenarios.

Completion criterion: either the plan is specific enough to execute mechanically, or you refuse under Vague Plan Refusal.

### 2. Workspace Gate

Inspect the current worktree and the nearest code, tests, configs, and analogous implementations before editing.

Completion criterion: you know which existing patterns to preserve, which files are safe to touch, and whether user changes or repo contradictions affect the plan.

### 3. Patch Gate

Apply the smallest coherent patch in dependency order: contracts or types first, core behavior next, callers or integration after that, focused tests last.

Completion criterion: every edit traces directly to a plan requirement, and no unrelated formatting or opportunistic cleanup is included.

### 4. Verification Gate

Run the narrowest useful tests or checks named by the plan. If the plan omits commands, run focused tests for the touched behavior, then the cheapest relevant broader check if risk justifies it.

Completion criterion: verification either passes, fails with concrete output, or is explicitly skipped with the blocking reason.

### 5. Report Gate

Produce a final implementation report.

Completion criterion: the report names the plan source, changed files, behavior implemented, tests run with results, skipped checks, and any exact follow-up needed.

## Vague Plan Refusal

Refuse implementation when the plan lacks any of:

- Concrete goal.
- Success criteria.
- Scope boundary.
- Target behavior.
- Verification path.

When refusing, state the missing items and recommend `plan-with-senior-dev` to turn the request into an executable plan. Do not make exploratory edits while trying to clarify a vague plan.

## Implementation Discipline

- Prefer local patterns over new abstractions.
- Add an abstraction only when the plan requires it or the repo already has the pattern for the same problem.
- Keep tests proportional to the patch risk and focused on the changed behavior.
- Treat generated files, lockfiles, migrations, public APIs, and snapshots as in scope only when the plan names them or the implementation cannot work without them.
- Stop and ask the user when the plan conflicts with repo facts, requires a missing secret or external system, or would force destructive git or filesystem operations.

## Final Report

Use this shape:

```markdown
Implemented the approved plan from [source].

Changed:
- [file]: [planned reason]

Verified:
- [command]: [result]

Skipped:
- [check]: [reason]

Follow-up:
- [only exact required follow-up, or "None"]
```
