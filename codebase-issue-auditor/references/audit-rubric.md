# Audit Rubric

Use this rubric before drafting any issue. The goal is useful, evidence-backed GitHub work, not a brainstorm.

## Categories

- `bug`: implemented behavior is wrong, crashes, loses data, violates a documented contract, or has a credible failing path.
- `security`: secrets exposure, auth/authz weakness, injection, unsafe deserialization, dependency vulnerability, or sensitive-data handling risk.
- `performance`: avoidable slow path, excessive I/O, unnecessary network calls, algorithmic scaling issue, expensive render loop, or measurable bottleneck.
- `test-gap`: important behavior lacks coverage, existing tests miss a high-risk path, or CI does not exercise a critical integration.
- `architecture`: module boundaries, interfaces, or dependencies make change risky or obscure; prefer findings with concrete locality or leverage evidence.
- `maintainability`: duplicated logic, fragile configuration, unclear ownership, dead code, or error handling that increases defect risk.
- `developer-experience`: setup, scripts, docs, CI feedback, or local workflows make normal development slower or error-prone.

## Ecosystem Optimization Evidence

Ecosystem optimization findings are valid when local framework, package, runtime, or tool usage leaves a documented capability unused or misconfigured.

Use ecosystem evidence for:

- `performance`: missed caching, compilation, runtime, rendering, bundling, query, or deployment capabilities that create avoidable work.
- `security`: vulnerable versions, missing hardening flags, unsafe defaults, or unconfigured security features documented by the vendor or project.
- `developer-experience`: package manager, test runner, build cache, CI, or local workflow features that would make normal development materially faster or clearer.
- `maintainability`: outdated configuration shape, deprecated APIs, duplicated tool responsibilities, or unsupported migration path with concrete local impact.
- `architecture`: framework or platform capabilities that would simplify boundaries, routing, data loading, module ownership, or deployment topology without inventing an unrelated abstraction.

Each ecosystem optimization finding needs local evidence, primary-source web evidence, and a concrete expected benefit. Do not draft broad modernization epics or "upgrade because newer exists" issues.

## Severity

- `critical`: likely data loss, security exposure, production outage, broken release path, or a defect that blocks most users.
- `high`: credible user-visible bug, significant security/performance risk, or a change blocker for important work.
- `medium`: concrete correctness, coverage, maintainability, or workflow issue that should be scheduled.
- `low`: useful cleanup or optimization with limited risk. Do not publish by default unless the user asks for low-priority backlog items.

## Confidence

- High confidence requires direct code evidence, reproducible command output, authoritative dependency metadata, or a clear path from implementation to failure.
- For ecosystem optimization findings, high confidence also requires current primary-source evidence such as official docs, release notes, migration guides, security advisories, package registry metadata, or vendor performance guidance.
- Medium confidence means the signal is credible but needs one more confirmation step. Keep it in the draft review but do not publish by default.
- Low confidence is speculation. Do not draft it as an issue.

## Default Publishing Threshold

Draft and publish only findings that are:

- severity `medium`, `high`, or `critical`;
- high confidence;
- independently fixable;
- supported by evidence that can be pasted into the issue.

## Issue Body Checklist

Each issue body should include:

- problem summary;
- why it matters;
- evidence with file paths, command output, dependency metadata, or reasoning;
- expected outcome;
- acceptance criteria;
- notes about likely affected area, without over-prescribing an implementation.
