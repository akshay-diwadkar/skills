---
name: optimize-codebase-with-senior-dev
description: Plan and, when explicitly requested, implement safe, evidence-backed codebase optimizations for runtime, frontend, backend, database, build, tests, CI/CD, dependencies, tooling, maintainability, architecture, and developer experience. Use after an approved audit finding, performance complaint, explicit optimization goal, DX pain, architecture concern, or modernization target when Codex should inventory the actual frameworks, packages, versions, and configuration; exploit supported native capabilities; and deliver measurable, minimal-side-effect, reversible changes with before/after verification.
---

# Optimize Codebase With Senior Dev

Answer: "What is the highest-leverage way to optimize this codebase or subsystem without breaking behavior?"

Work only from a stated target or observed evidence. Preserve behavior unless the user explicitly approves a change. Prefer deeper use of proven capabilities already present in the stack over custom machinery, new dependencies, upgrades, or broad rewrites.

Planning is the default. Implement only when the user explicitly requests code changes.

## Boundary

This is not a broad issue-discovery or issue-publishing skill. Start from an explicit optimization goal, approved finding, complaint, DX pain, architecture concern, or modernization target. Use `codebase-issue-auditor` when the work is to discover and prove issues.

## Reference Routing

For non-trivial work, read:

- `references/optimization-protocol.md` before creating baselines, candidate ledgers, plans, execution records, or verification records.
- `references/ecosystem-leverage.md` whenever a framework, package, runtime, database, build tool, test tool, CI system, or deployment platform affects the target.
- `references/optimization-rubric.md` before ranking candidates or authorizing implementation.
- `references/optimization-patterns.md` when selecting patterns or checking anti-patterns.

## Workflow

### A. Grill the Optimization Brief

Ask focused questions only when the user has not supplied enough context. Capture:

- target repo/path and affected workflow;
- goal, pain signal, and optimization category;
- constraints, exclusions, success metric, and acceptable risk;
- plan-only or implementation request;
- required output format.

Use an approved audit finding as the brief when supplied. Complete only when you can restate the target, goal, constraints, metric, risk tolerance, and authorization level.

### B. Frame the System

Inspect repo guidance and local evidence before proposing changes:

- `AGENTS.md`, `CLAUDE.md`, `CONTEXT.md`, README files, docs, and ADRs;
- manifests, lockfiles, version files, package-manager and workspace config;
- build, test, lint, CI, deployment, runtime, database, and observability config;
- existing benchmarks, profiles, source paths, and regression tests.

State repo purpose, relevant subsystem, runtime/tooling, deployment shape, and verification surface. Complete only when the target workflow can be traced through the relevant code and configuration.

### C. Build the Ecosystem Leverage Map

Inventory only the ecosystem components that can affect the target. Record runtimes, frameworks, direct and development dependencies, lockfile-resolved versions, plugins, integrations, build/test tools, deployment platforms, and relevant configuration.

Classify each relevant component as declared, resolved, configured, actively used, duplicated by custom code, or transitive-only. Map the measured pain to capabilities supported by the installed version.

Inspect local config, package metadata, types, source, and bundled docs first. When a recommendation depends on package or framework behavior, confirm it with official version-matched documentation. Complete only when every ecosystem-based candidate has local evidence, version compatibility evidence, and a concrete link to the target.

### D. Establish the Baseline

Do not optimize from vibes. Collect cheap, safe evidence such as timings, profiles, build/test/lint output, bundle stats, query plans, dependency metadata, code-path analysis, or complexity/coupling evidence.

Record command, environment, workload, raw result, variance, limitations, and confidence. If measurement is impossible, explain why and downgrade static evidence accordingly. Complete only when the proposed success metric has a reproducible baseline or an explicit measurement blocker.

### E. Generate Candidate Optimizations

Generate multiple candidates, including relevant comparisons among:

- configuring an existing capability;
- adopting an unused framework-native or direct-dependency capability;
- replacing custom code that duplicates supported behavior;
- simplifying redundant wrappers or integrations;
- making a focused local code change;
- adding a dependency only when it reduces net complexity;
- upgrading only when a specific required capability or fix is unavailable locally.

For each candidate record leverage point, expected benefit, affected files/subsystems, ecosystem fit, version compatibility, effort, risk, blast radius, reversibility, operational cost, net-complexity effect, verification path, and side effects.

Prefer small, independently reviewable candidates. Put speculative, broad, or unmeasurable options in the reject ledger.

### F. Rank and Choose

Apply `references/optimization-rubric.md`. Prefer the smallest safe candidate with measurable impact, strong ecosystem fit, compatible local versions, low operational cost, and a reliable rollback.

Separate quick wins from deeper refactors and unrelated optimizations into separate PR-sized plans. Complete only when the recommendation beats the rejected alternatives under the user's constraints.

### G. Plan or Execute

For plan-only work, produce the recommended strategy, exact file areas, ordered changes, guardrails, checks, acceptance criteria, rollback, and residual risks. Produce a one-shot Codex goal prompt when requested.

For explicitly authorized implementation:

1. Confirm baseline and regression coverage before editing.
2. Apply one independently measurable candidate as a minimal patch.
3. Run focused behavior checks after each meaningful change.
4. Re-run the baseline under comparable conditions.
5. Continue to another candidate only when it is independently authorized by the brief and the previous result is understood.

Stop and narrow or revert the optimization patch you introduced when behavior regresses, compatibility evidence fails, or the measured benefit is inconclusive. Do not revert unrelated user changes.

### H. Verify and Report

Compare raw before/after results and account for variance, cache state, workload, and environment. Confirm public behavior, correctness, types, validation, tests, and operational semantics remain intact.

Do not claim success without evidence. If the result is neutral or worse, report it honestly and recommend keeping, narrowing, or reverting based on the stated goal, including maintainability goals that may rely on static evidence.

Complete only when the report includes ecosystem fit, version evidence, before/after evidence, regression checks, rollback status, and residual risks.

## Guardrails

- No optimization without a target and evidence.
- No broad rewrites, speculative abstractions, or unrelated optimization bundles by default.
- No public API or behavior changes without explicit approval.
- No framework feature recommendation without confirming framework, resolved version, configuration, execution mode, and target code path.
- No documentation from a newer major version as evidence for the installed version.
- No upgrade merely because a newer version exists; require a specific local benefit and compatibility plan.
- No assumption that every installed package is beneficial; account for runtime, bundle, maintenance, security, and overlap costs.
- No direct import of a transitive dependency unless it becomes declared and compatibility ownership is accepted.
- No caching, memoization, concurrency, lazy loading, indexes, workers, batching, pooling, or parallelism without workload evidence and correctness controls.
- No deleting tests or weakening types, lint, validation, or release gates merely to improve speed.
- Prefer reversible changes and split high-risk or unrelated work into separate PRs.

## Output Modes

- Local optimization report.
- Ecosystem leverage report.
- Implementation plan or Codex-ready prompt.
- Patch plan or explicitly authorized implementation run.
- Before/after verification report.
- Follow-up after implementation.
- GitHub issue update note; never publish issues from this skill.

## Handoff Guidance

- Use `codebase-issue-auditor` to discover and prove issues.
- Use `plan-with-senior-dev` for general implementation planning without an optimization target.
- Use `improve-codebase-architecture` when the primary goal is architectural redesign rather than measurable optimization.
- Use `diagnose` first when concrete failing behavior or a performance regression must be reproduced.
