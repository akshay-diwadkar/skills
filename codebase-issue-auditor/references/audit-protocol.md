# Audit Protocol

Use this protocol to reduce missed findings. Keep the artifacts in working notes unless the user asks for a report.

## Repo Frame

Record the local frame before judging findings:

- repo purpose and primary user or operator workflow;
- languages, runtimes, package managers, and lockfiles;
- app frameworks, major libraries, and generated-code boundaries;
- build, lint, type-check, test, coverage, and CI commands;
- deployment, packaging, database, queue, cache, observability, and security surfaces;
- domain docs, ADRs, issue conventions, and ownership guidance.

This frame is complete when later audit judgments can cite where each important subsystem, tool, and workflow lives.

## Ecosystem Inventory

Build an inventory from local evidence only:

- manifests, lockfiles, version files, framework configs, build/test configs, CI files, Dockerfiles, deployment config, and runtime/tooling files;
- versions and config choices that materially affect build, test, runtime, security, deploy, or developer workflow;
- missing manifests or configs that are themselves relevant to risk.

Read `ecosystem-optimization.md` only after this inventory identifies a concrete local tool or framework candidate. External research supplements local evidence; it does not create a finding by itself.

## Risk Map

Map likely failure zones before deep inspection:

- externally reachable routes, commands, jobs, hooks, and scheduled work;
- auth, authorization, secrets, data access, mutations, migrations, imports, exports, billing, and destructive operations;
- concurrency, caching, retries, batching, pagination, time zones, serialization, and file/network boundaries;
- tests that claim coverage of critical behavior, plus critical behavior with no visible tests;
- code owners or module boundaries that make changes risky.

The risk map is complete when every high-impact behavior has at least one source location, config file, test, or explicit "not found" note.

## Coverage Matrix

Audit through these passes. For each pass, record accepted candidates and rejects.

- `bug`: contracts, edge cases, error paths, data integrity, state transitions, null/empty handling, and user-visible behavior.
- `security`: auth/authz, injection, secrets, dependency vulnerabilities, unsafe deserialization, sensitive data, redirects, uploads, and permission boundaries.
- `performance`: repeated I/O, avoidable network calls, expensive render/query loops, algorithmic scaling, caching, batching, and startup/build hotspots.
- `test-gap`: critical paths without tests, tests that miss meaningful assertions, unexercised integrations, skipped/flaky tests, and CI gaps.
- `architecture`: unclear boundaries, hidden coupling, ownership ambiguity, misplaced policy, cross-layer dependencies, and changes requiring broad edits.
- `maintainability`: duplication, dead code, fragile config, unclear error handling, stale docs, and unsupported compatibility paths.
- `developer-experience`: slow or misleading scripts, incomplete setup docs, missing local checks, noisy CI, and hard-to-debug tool failures.

A pass is complete when the main files and configs for that category have been inspected, relevant commands have been run when cheap and safe, and each plausible candidate has an evidence or reject entry.

## Candidate Ledger

Track every plausible finding until it is accepted or rejected:

- working title;
- category, severity, and confidence;
- suspected root cause, not just symptom;
- local evidence: file paths, command output, dependency metadata, test evidence, or reasoning chain;
- external evidence when ecosystem optimization or security advisory claims are involved;
- expected impact and affected workflow;
- verification path for confirming the fix;
- decision: accepted, merged into another candidate, deferred, or rejected.

Do not draft directly from a first impression. Promote only candidates whose root cause and evidence survive the rubric.

## Reject Ledger

Record why plausible candidates were not drafted:

- insufficient evidence;
- duplicate symptom of another root cause;
- severity below the default threshold;
- medium or low confidence;
- too broad to be independently fixable;
- expected benefit unclear;
- contradicted by source, tests, docs, or command output.

The reject ledger prevents re-raising weak ideas as findings and gives the user useful audit context without turning speculation into issues.

## Final Threshold

Before drafting, reconcile the coverage matrix and ledgers:

- every high-risk area has an accepted candidate or reject reason;
- every accepted candidate maps to one root cause;
- every accepted candidate passes the rubric's default publishing threshold;
- ecosystem candidates have both local evidence and current primary-source evidence;
- low-severity or medium-confidence candidates are held back unless the user asks for backlog material.

The protocol is complete when the issue list is smaller than the candidate ledger, and every omission has a reason.
