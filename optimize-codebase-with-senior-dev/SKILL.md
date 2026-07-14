---
name: optimize-codebase-with-senior-dev
description: Plan and, when explicitly requested, implement safe, evidence-backed codebase optimizations for runtime, frontend, backend, database, build, tests, CI/CD, dependencies, tooling, maintainability, architecture, and developer experience. Use after an approved audit finding, performance complaint, explicit optimization goal, DX pain, architecture concern, modernization target, or when asked to broadly discover optimization opportunities across a codebase. The skill deeply comprehends the repo, actively researches official framework and library documentation via web search to find underexploited capabilities, produces an ROI-ranked optimization ledger, and generates structured briefs for plan-with-senior-dev.
---

# Optimize Codebase With Senior Dev

Answer: "What is the highest-leverage way to optimize this codebase or subsystem without breaking behavior?"

Two modes of operation:

- **Targeted mode**: start from a stated target, pain signal, or approved finding. Optimize the specific area.
- **Sweep mode**: when no specific target is given, systematically analyze the entire stack to discover and rank all optimization opportunities.

In both modes: work from evidence, not vibes. Preserve behavior unless the user explicitly approves a change. Prefer deeper use of proven capabilities already present in the stack over custom machinery, new dependencies, upgrades, or broad rewrites.

Planning is the default. Implement only when the user explicitly requests code changes.

## Boundary

This is not a broad issue-discovery or issue-publishing skill. In targeted mode, start from an explicit optimization goal, approved finding, complaint, DX pain, architecture concern, or modernization target. In sweep mode, start from an explicit request to "find optimizations" or "optimize everything." Use `codebase-issue-auditor` when the work is to discover and prove bugs, risks, or architectural issues rather than optimize performance and capabilities.

## Reference Routing

For non-trivial work, read:

- `references/optimization-protocol.md` before creating baselines, candidate ledgers, plans, execution records, or verification records.
- `references/ecosystem-leverage.md` whenever a framework, package, runtime, database, build tool, test tool, CI system, or deployment platform affects the target.
- `references/docs-research-protocol.md` before researching official documentation for any framework, library, or tool.
- `references/optimization-rubric.md` before ranking candidates, computing ROI scores, or authorizing implementation.
- `references/optimization-patterns.md` when selecting patterns or checking anti-patterns.

## Workflow

### A. Grill the Optimization Brief

Ask focused questions only when the user has not supplied enough context. Capture:

- target repo/path and affected workflow, or confirmation of sweep mode;
- goal, pain signal, and optimization category (or "broad optimization" for sweep);
- constraints, exclusions, success metric, and acceptable risk;
- plan-only or implementation request;
- required output format.

Use an approved audit finding as the brief when supplied. In sweep mode, the brief is "discover and rank all optimization opportunities in this repo."

Complete only when you can restate the target (or sweep scope), goal, constraints, metric, risk tolerance, and authorization level.

### B. Deep Repo Comprehension

Go beyond config files. Build a thorough mental model of what the repo does and how it works.

#### B.1 Read All Guidance

- `AGENTS.md`, `CLAUDE.md`, `CONTEXT.md`, README files, docs, and ADRs;
- manifests, lockfiles, version files, package-manager and workspace config;
- build, test, lint, CI, deployment, runtime, database, and observability config;
- existing benchmarks, profiles, source paths, and regression tests.

#### B.2 Trace Workflows End-to-End

In targeted mode, trace the target workflow. In sweep mode, trace every major workflow:

- Identify entry points (API endpoints, CLI commands, scheduled jobs, event handlers, UI pages, training scripts, pipeline definitions).
- For each entry point, trace: input → validation → core logic → data access → external calls → transformation → output/side-effects.
- Record the exact code path with file:line references.
- Note performance-relevant characteristics: data volumes, loop structures, I/O patterns, serialization boundaries, concurrency model.

#### B.3 Build the Component Usage Map

For every framework, library, tool, runtime, and platform identified:

- Record what it is, its resolved version, and how the repo actually uses it (not just that it's installed).
- Classify usage: configuration-driven, API-driven, custom wrappers, partial adoption, or unused-but-installed.
- Map which workflows depend on which components.
- Note any custom code that might duplicate library capabilities.

#### B.4 Map Component Interactions

Identify how components interact at boundaries:

- What data formats cross boundaries (JSON, Pickle, Parquet, Arrow, CSV, Protobuf, custom);
- What connection/client patterns are used (per-request, pooled, persistent, shared);
- Where serialization/deserialization happens;
- What orchestration patterns exist (synchronous, async, event-driven, polling, batch).

State repo purpose, architecture, relevant subsystems, runtime/tooling, deployment shape, verification surface, and component interaction map. Complete only when every workflow on the target path can be traced through code and configuration.

### C. Live Documentation Research

Read `references/docs-research-protocol.md` before starting this phase.

For every significant framework, library, tool, and platform identified in Phase B, actively research official documentation to find optimization opportunities the repo is not currently exploiting.

#### C.1 Identify Research Targets

Prioritize components that:

- Handle performance-sensitive workflows (training, inference, data pipelines, API serving, builds, deployments);
- Have rich configuration surfaces (many tunable parameters);
- Are core frameworks with deep feature sets likely only partially adopted;
- Are infrastructure components (Spark, Kubernetes, databases, CI platforms) with performance tuning guides;
- Show signs of default configuration or minimal customization in the repo.

#### C.2 Research Each Component

For each research target, use web search and URL reading to find and read:

- Official documentation for the resolved version;
- Performance tuning guides and best practices;
- Configuration references (especially parameters the repo hasn't set);
- Changelog and what's-new for the installed version (capabilities available but unused);
- Known performance pitfalls and anti-patterns.

Search queries should be specific and version-matched:

- `{library} {version} performance tuning`
- `{library} {version} configuration reference`
- `{library} best practices production deployment`
- `{framework} {version} optimization guide`

#### C.3 Cross-Reference Against Repo Usage

For each finding from documentation research, compare:

- What the repo configures vs. what the docs say CAN be configured;
- What the repo implements in custom code vs. what the library provides natively;
- What parameters are at defaults vs. what the docs recommend for production workloads;
- What the repo's deployment model is vs. what the docs recommend for that model.

The delta between "what the repo does" and "what the docs say is possible or recommended" is the optimization surface.

#### C.4 Record in Documentation Research Log

For each finding, record: component, version, doc URL, specific finding, current repo state, recommended state, expected benefit, confidence, and compatibility notes. See `references/docs-research-protocol.md` for the full format.

Complete only when every significant component has been researched and cross-referenced, and findings are recorded with version-matched evidence.

### D. Optimization Surface Discovery

Synthesize the repo comprehension (Phase B) and documentation research (Phase C) into a structured optimization surface.

#### D.1 Single-Component Opportunities

For each component, identify optimizations from:

- Configuration options not currently set that the docs recommend;
- Native capabilities that could replace custom code;
- Anti-patterns the docs warn about that the repo exhibits;
- Advanced features in the installed version that the repo doesn't use;
- Default values that are suboptimal for the repo's workload characteristics.

#### D.2 Cross-Component Opportunities

Read the Cross-Component Optimization section of `references/ecosystem-leverage.md`. Identify optimizations at component boundaries:

- Serialization format mismatches between components;
- Redundant data transformations across boundaries;
- Connection/client reuse opportunities;
- Batch size mismatches between producers and consumers;
- Duplicate computation across components;
- Orchestration overhead that could be eliminated.

#### D.3 Domain-Specific Passes

Run the domain-specific optimization passes from `references/ecosystem-leverage.md` and `references/docs-research-protocol.md`, but now informed by the live documentation research. Only run passes connected to the target (targeted mode) or all applicable passes (sweep mode).

For each finding, record: what the repo does now, what could be done instead, the evidence source (code path + doc reference), and the expected benefit.

Complete only when the optimization surface is fully mapped with evidence for each finding.

### E. Establish the Baseline

Do not optimize from vibes. Collect cheap, safe evidence such as timings, profiles, build/test/lint output, bundle stats, query plans, dependency metadata, code-path analysis, or complexity/coupling evidence.

Record command, environment, workload, raw result, variance, limitations, and confidence. If measurement is impossible, explain why and downgrade static evidence accordingly.

In sweep mode, establish baselines for the highest-priority candidates first. Not every candidate needs a baseline before ranking — low-effort candidates with clear code-path evidence can be ranked on static analysis alone.

Complete only when the proposed success metric has a reproducible baseline or an explicit measurement blocker.

### F. ROI-Ranked Candidate Ledger

Read `references/optimization-rubric.md` before scoring.

#### F.1 Generate Candidates

Generate multiple candidates from the optimization surface (Phase D), including relevant comparisons among:

- configuring an existing capability;
- adopting an unused framework-native or direct-dependency capability;
- replacing custom code that duplicates supported behavior;
- simplifying redundant wrappers or integrations;
- making a focused local code change;
- optimizing cross-component boundaries;
- adding a dependency only when it reduces net complexity;
- upgrading only when a specific required capability or fix is unavailable locally.

For each candidate record: leverage point, expected benefit, affected files/subsystems, ecosystem fit, version compatibility, effort, risk, blast radius, reversibility, operational cost, net-complexity effect, verification path, side effects, and evidence sources.

#### F.2 Score and Rank

Apply the ROI scoring formula from `references/optimization-rubric.md`:

ROI = (Impact × Confidence) / (Effort × Risk)

Assign each candidate to a tier:

- **Quick Win** (ROI ≥ 4.0): High impact, low effort, low risk. Recommend first.
- **Strategic Win** (1.5 ≤ ROI < 4.0): High impact, needs proper planning. Hand off to `plan-with-senior-dev`.
- **Speculative** (0.5 ≤ ROI < 1.5): Uncertain benefit. Recommend further investigation.
- **Rejected** (ROI < 0.5 or fails threshold): Record in reject ledger with reason and revisit condition.

Within each tier, order by ROI score (descending), blast radius (ascending), reversibility (most reversible first), and independence (no dependencies on other candidates first).

#### F.3 Produce the Ranked Ledger

For each candidate, produce a summary with: title, what changes, why it helps, expected benefit, effort estimate, risk, evidence sources, and ROI score. See `references/optimization-rubric.md` for the full format.

Separate quick wins from deeper work and unrelated optimizations. Complete only when every candidate beats the rejected alternatives under the user's constraints, and the tiered list is ordered by ROI.

### G. Plan Generation

For plan-only work, produce the recommended strategy per tier:

- **Quick Wins**: direct implementation guidance with exact file areas, ordered changes, guardrails, checks, acceptance criteria, and rollback.
- **Strategic Wins**: a structured handoff brief for `plan-with-senior-dev` containing: target, goal, constraints, success criteria, affected files/subsystems, ecosystem evidence with doc URLs, baseline reference, verification approach, and residual risks.
- **Speculative**: the missing evidence and recommended investigation steps.

When `plan-with-senior-dev` is available, explicitly recommend using it for Strategic Win candidates. The handoff brief should contain enough context for `plan-with-senior-dev` to produce a decision-complete implementation specification without re-researching the codebase or docs.

For explicitly authorized implementation:

1. Confirm baseline and regression coverage before editing.
2. Apply one independently measurable candidate as a minimal patch.
3. Run focused behavior checks after each meaningful change.
4. Re-run the baseline under comparable conditions.
5. Continue to another candidate only when it is independently authorized by the brief and the previous result is understood.

Stop and narrow or revert the optimization patch you introduced when behavior regresses, compatibility evidence fails, or the measured benefit is inconclusive. Do not revert unrelated user changes.

When `implement-with-senior-dev` is available, recommend using it for implementation work that follows an approved plan.

### H. Verify and Report

Compare raw before/after results and account for variance, cache state, workload, and environment. Confirm public behavior, correctness, types, validation, tests, and operational semantics remain intact.

Validate ROI: does the measured improvement match the expected benefit from the candidate ledger? If not, explain the discrepancy and adjust the ROI score for remaining candidates from the same evidence source.

Do not claim success without evidence. If the result is neutral or worse, report it honestly and recommend keeping, narrowing, or reverting based on the stated goal, including maintainability goals that may rely on static evidence.

Complete only when the report includes ecosystem fit, version evidence, doc research references, before/after evidence, regression checks, ROI validation, rollback status, and residual risks.

## Guardrails

- No optimization without a target (targeted mode) or an explicit sweep request (sweep mode).
- No broad rewrites, speculative abstractions, or unrelated optimization bundles by default.
- No public API or behavior changes without explicit approval.
- No framework feature recommendation without confirming framework, resolved version, configuration, execution mode, and target code path.
- No documentation from a newer major version as evidence for the installed version.
- No upgrade merely because a newer version exists; require a specific local benefit and compatibility plan.
- No assumption that every installed package is beneficial; account for runtime, bundle, maintenance, security, and overlap costs.
- No direct import of a transitive dependency unless it becomes declared and compatibility ownership is accepted.
- No caching, memoization, concurrency, lazy loading, indexes, workers, batching, pooling, or parallelism without workload evidence and correctness controls.
- No deleting tests or weakening types, lint, validation, or release gates merely to improve speed.
- No documentation research claim without a specific URL and version match.
- No ROI score without explicit Impact, Confidence, Effort, and Risk ratings.
- Prefer reversible changes and split high-risk or unrelated work into separate PRs.

## Output Modes

- Local optimization report.
- Ecosystem leverage report.
- ROI-ranked optimization ledger with tiered candidates.
- Documentation research log with findings and evidence.
- Optimization surface analysis.
- Plan-with-senior-dev handoff brief for strategic candidates.
- Implementation plan or Codex-ready prompt.
- Patch plan or explicitly authorized implementation run.
- Before/after verification report with ROI validation.
- Follow-up after implementation.
- GitHub issue update note; never publish issues from this skill.

## Handoff Guidance

- Use `codebase-issue-auditor` to discover and prove bugs, risks, and architectural issues.
- Use `plan-with-senior-dev` to turn Strategic Win candidates into decision-complete implementation plans. Pass the structured handoff brief from Phase G.
- Use `implement-with-senior-dev` to execute an approved implementation plan as a minimal patch.
- Use `improve-codebase-architecture` when the primary goal is architectural redesign rather than measurable optimization.
- Use `diagnose` first when concrete failing behavior or a performance regression must be reproduced.
