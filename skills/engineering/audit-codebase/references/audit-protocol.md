# Audit Protocol

Use this protocol to build the audit bundle. The bundle is the audit's coverage proof; an issue list alone is not a complete audit.

## 1. Establish the frame

Record:

- target path, audited commit, and dirty-worktree state;
- requested categories, severity threshold, exclusions, time box, output mode, and limitations;
- repository purpose, user/operator workflows, runtimes, package managers, and lockfiles;
- repository and generated/vendor boundaries;
- build, lint, type-check, test, coverage, and CI commands with observed results or a reason they were not run;
- deployment, packaging, database, queue, cache, observability, secrets, and destructive-operation surfaces;
- subsystems with stable IDs, paths, and risk levels.

Inspect first. Ask the user only about intent that local evidence cannot resolve. A time box narrows inspection but never disappears: record uninspected surfaces as deferred limitations.

**Completion gate:** every required `audit_context` and `repository_inventory` field in `audit-bundle.md` is populated from evidence, including at least one subsystem and baseline-command record.

## 2. Reconcile the audit request with evidence

After establishing the frame, maintain a temporary ledger with one row per possible gap:

`request statement | repository evidence | audit consequence | options | recommendation and reason | answer | status`

Record conflicts, missing intent, scope mismatches, hidden repository boundaries, and undefined category, severity, priority, exclusion, output, limitation, or publication preferences. A gap is blocking only when resolving it could materially change audit coverage, promotion priority, reported limitations, output, or publication intent. Resolve repository facts by inspecting further and use declared defaults for low-impact reversible details; do not ask the user about either.

For blocking gaps, ask up to three closely related questions per round. State the request and grounded evidence, explain the affected audit decision, offer two to four mutually exclusive options when feasible, and identify the recommended option with a reason based on risk, repository conventions, coverage integrity, and the smallest safe assumption. Use scoped free text only when the answer space cannot be bounded honestly.

Record answers and re-inspect any changed boundary. Repeat until all gaps are resolved or reclassified as non-blocking. When answers materially change the audit frame, recap the target, categories, severity threshold, priorities, exclusions, limitations, output, and publication intent and require explicit confirmation. Alignment confirmation is not publication approval. If a blocking gap remains unanswered, pause and report it rather than presenting the audit as complete.

Fold confirmed outcomes into existing audit context, inventory, coverage, and limitation fields, then discard the ledger. Do not add gap records to the audit bundle.

**Completion gate:** no blocking request-to-evidence gap remains, and any materially changed audit frame is explicitly confirmed.

## 3. Build the risk map

Create a risk surface for every externally reachable or high-impact behavior, including:

- routes, commands, jobs, hooks, schedulers, imports, exports, and deployment entry points;
- authentication, authorization, secrets, mutations, migrations, billing, and destructive actions;
- file/network boundaries, serialization, time zones, pagination, batching, caching, retries, and concurrency;
- critical behavior claimed by tests and critical behavior with no visible tests;
- high-churn, broadly imported, or weakly owned modules where changes have wide blast radius.

Give each surface locations, categories, validation actions, and a final status. `accepted` links candidates, `rejected` links reject records, `clean` records the evidence that cleared it, and `deferred` records why it was not resolved.

**Completion gate:** every high or critical surface has a terminal status and no surface relies on an empty location or validation list.

## 4. Cover every subsystem/category pair

Create one coverage record for every inventoried subsystem and selected category:

- `bug`: contracts, state transitions, edge/error paths, data integrity, and user-visible behavior;
- `security`: auth/authz, injection, secrets, unsafe parsing, sensitive data, uploads, redirects, and dependency exposure;
- `performance`: repeated I/O, query/render loops, network calls, scaling, caching, batching, startup, and build paths;
- `test-gap`: critical paths, meaningful assertions, integrations, skipped/flaky tests, and CI execution;
- `architecture`: boundaries, policy placement, dependency direction, hidden coupling, and broad-change leverage;
- `maintainability`: duplication, dead code, fragile configuration, stale compatibility paths, and error ownership;
- `developer-experience`: setup, scripts, local checks, CI feedback, diagnostics, and debugging friction.

Use `complete`, `not-applicable`, or `deferred`. Record inspected locations, methods/commands, candidate and reject links, and a conclusion. Never use `not-applicable` without a repository-specific reason.

After category coverage, run every applicable discovery pattern in `deep-analysis-patterns.md`. Deep findings must cross files or system boundaries; single-file findings remain valid standard candidates.

**Completion gate:** the coverage matrix contains every required subsystem/category pair exactly once, and every applicable deep pattern has an investigation result in candidate/reject evidence or a coverage conclusion.

## 5. Maintain candidate and reject ledgers

For each plausible root cause, record the full candidate contract from `audit-bundle.md`. Seek disconfirming evidence before deciding:

- inspect guards, callers, tests, framework/runtime guarantees, reachability, and generated/vendor boundaries;
- run a focused reproduction when safe and proportionate;
- distinguish an observed failure from a reasoned failure path;
- merge symptoms with the same root cause;
- compare current code and open issue titles when issue metadata is available.

Rejected, deferred, and merged candidates require a reject record explaining the decision. Do not erase near-misses: they prove that a signal was investigated rather than missed.

**Completion gate:** every candidate has a terminal decision, every non-accepted candidate has a reject record, and every accepted candidate passes `audit-rubric.md`.

## 6. Reconcile the audit

Link exactly one issue draft to every accepted candidate, validate the bundle, and repair every validator error before review. Summarize accepted issues, rejected near-misses, deferred surfaces, failed or skipped baseline commands, and dirty-worktree limitations.

**Completion gate:** `validate_audit_bundle.py` exits successfully, accepted candidates and issues are one-to-one, and every omitted area has an explicit clean, reject, defer, not-applicable, or scope-limitation record.
