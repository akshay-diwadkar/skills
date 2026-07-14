# Audit Rubric

Use this rubric to decide which candidates from the audit protocol become GitHub issue drafts. The goal is useful, evidence-backed work, not a brainstorm.

## Categories

- `bug`: implemented behavior is wrong, crashes, loses data, violates a documented contract, or has a credible failing path.
- `security`: secrets exposure, auth/authz weakness, injection, unsafe deserialization, dependency vulnerability, or sensitive-data handling risk.
- `performance`: avoidable slow path, excessive I/O, unnecessary network calls, algorithmic scaling issue, expensive render loop, or measurable bottleneck.
- `test-gap`: important behavior lacks coverage, existing tests miss a high-risk path, or CI does not exercise a critical integration.
- `architecture`: module boundaries, interfaces, ownership, or dependencies make change risky or obscure; prefer findings with concrete locality or leverage evidence.
- `maintainability`: duplicated logic, fragile configuration, unclear ownership, dead code, or error handling that increases defect risk.
- `developer-experience`: setup, scripts, docs, CI feedback, or local workflows make normal development slower or error-prone.

## Evidence Gate

Accept a candidate only when it has all of these:

- root cause: the issue identifies the underlying implementation, configuration, dependency, or workflow cause rather than only a symptom;
- local evidence: source locations, command output, dependency metadata, test evidence, documentation, or a clear reasoning chain from implementation to failure;
- impact: the affected user, operator, maintainer, build, test, or runtime workflow is named;
- verification path: a concrete way to know the fix worked, such as a regression test, command, manual reproduction, benchmark, config check, or clean rerun;
- acceptance criteria: observable criteria a maintainer can use to close the issue.

Reject candidates that require guessing about product intent, hidden production state, unavailable logs, or unobserved user behavior unless the local code creates a credible failure path.

## Cross-Cutting & Deep Analysis Evidence

Deep analysis findings from `deep-analysis-patterns.md` must meet the standard evidence gate above AND the additional requirements below.

### Cross-file evidence requirement

Every deep analysis finding must cite evidence from at least two files or two distinct system boundaries. Single-file issues are already covered by the standard coverage matrix passes. If the entire finding is contained in one file, it belongs in a standard category pass, not the deep analysis.

### Minimum evidence bar by pattern

- Semantic contract drift: show both the changed contract (source, type, or behavior) AND at least one mismatched call-site or test. A changed function without a broken caller is not a finding.
- Implicit ordering dependencies: show two or more operations whose order matters AND the absence of an enforcement mechanism. Sequential code that happens to be ordered is not a finding.
- Error swallowing: show the catch or fallback AND the code path where no caller, user, or operator can detect the failure. Intentional silent handling with a clear comment or design rationale is a reject.
- Stale cross-references: show the reference on one side AND the missing definition or consumer on the other. Dead CSS in a component library is a reject.
- Temporal coupling: show the shared mutable state AND the concurrent access path AND the absence of synchronization. Single-threaded code with no concurrent entry is not a race condition.
- Boundary mismatches: show the encoding or format on the producing side AND the different assumption on the consuming side AND a concrete value that would be corrupted.
- Default value traps: show the fallback mechanism AND a legitimate input value it would override AND the resulting incorrect behavior.
- Observability gaps: show the diagnostic mechanism AND the gap between what it claims to verify and what it actually verifies.
- Dependency graph shadows: show the import in production code AND the dependency's absence from or incorrect position in the manifest.
- Incomplete lifecycle: show the resource acquisition AND a concrete code path where the release does not execute. Resources managed by framework lifecycle guarantees that apply here are a reject.
- Invariant violations: show the boundary assertion or type AND the concrete mismatch with actual data crossing the boundary. Type assertions followed by immediate validation are a reject.
- Git-history signals: show the historical signal AND a concrete current-state risk. High churn alone is not a finding; high churn plus low coverage plus active bugs IS a finding.

### False-positive guardrails

Reject deep analysis candidates when:

- the pattern matches syntactically but the code has an explicit guard, comment, or design rationale that makes the pattern intentional;
- the affected code path is dead, unreachable, or behind a feature flag that is permanently off;
- a framework or runtime guarantee makes the theoretical issue impossible in practice (e.g., single-threaded event loop eliminates a race condition, GC eliminates a resource leak);
- the evidence comes from test-only code, generated code, or vendored third-party code;
- the finding duplicates a candidate already raised by a standard coverage pass.

## Ecosystem Optimization Evidence

Ecosystem optimization findings are valid only when local framework, package, runtime, or tool usage leaves a documented capability unused or misconfigured.

Use ecosystem evidence for:

- `performance`: missed caching, compilation, runtime, rendering, bundling, query, or deployment capabilities that create avoidable work.
- `security`: vulnerable versions, missing hardening flags, unsafe defaults, or unconfigured security features documented by the vendor or project.
- `developer-experience`: package manager, test runner, build cache, CI, or local workflow features that would make normal development materially faster or clearer.
- `maintainability`: outdated configuration shape, deprecated APIs, duplicated tool responsibilities, or unsupported migration path with concrete local impact.
- `architecture`: framework or platform capabilities that would simplify boundaries, routing, data loading, module ownership, or deployment topology without inventing an unrelated abstraction.

Each ecosystem optimization finding needs local evidence, current primary-source web evidence, and a concrete expected benefit. Do not draft broad modernization epics or "upgrade because newer exists" issues.

## Severity

- `critical`: likely data loss, security exposure, production outage, broken release path, or a defect that blocks most users.
- `high`: credible user-visible bug, significant security/performance risk, or a change blocker for important work.
- `medium`: concrete correctness, coverage, maintainability, or workflow issue that should be scheduled.
- `low`: useful cleanup or optimization with limited risk. Do not publish by default unless the user asks for low-priority backlog items.

## Confidence

- High confidence requires direct code evidence, reproducible command output, authoritative dependency metadata, test evidence, or a clear path from implementation to failure.
- For ecosystem optimization findings, high confidence also requires current primary-source evidence such as official docs, release notes, migration guides, security advisories, package registry metadata, or vendor performance guidance.
- Medium confidence means the signal is credible but needs one more confirmation step. Keep it in the draft review only if useful context is worth showing; do not publish by default.
- Low confidence is speculation. Do not draft it as an issue.

## Default Publishing Threshold

Draft and publish only findings that are:

- severity `medium`, `high`, or `critical`;
- high confidence;
- independently fixable;
- rooted in one cause rather than a broad area;
- supported by evidence that can be pasted into the issue;
- paired with a verification path and acceptance criteria.

## Issue Body Checklist

Each issue body should include:

- problem summary;
- why it matters and who or what workflow is affected;
- root cause;
- evidence with file paths, command output, dependency metadata, docs, or reasoning;
- expected outcome;
- verification path;
- acceptance criteria;
- notes about likely affected area, without over-prescribing an implementation.
