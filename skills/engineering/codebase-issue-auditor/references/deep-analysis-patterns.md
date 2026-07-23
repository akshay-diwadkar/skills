# Deep Analysis Patterns

Use these as cross-file discovery lenses after standard category coverage. Select every pattern with a plausible target in the repository frame. Record the investigation result; apply `audit-rubric.md` only after discovery.

| Pattern | Inspect | Promote only with |
| --- | --- | --- |
| `semantic-contract-drift` | Shared interfaces, changed functions, call sites, tests, generated clients | Contract evidence and a mismatched caller/test |
| `implicit-ordering-dependency` | Bootstrap, middleware, migrations, handlers, hooks, config loading | Order-sensitive operations and missing enforcement |
| `silent-error-degradation` | Catch/fallback/retry paths, error boundaries, jobs, integrations | Consumed failure and no caller/operator signal |
| `phantom-cross-reference` | Env vars, feature flags, routes, schemas, config keys, assets | Present reference and missing/incompatible counterpart |
| `temporal-coupling-or-race` | Read-modify-write, caches, files, async work, shared state | Mutable resource, concurrent path, and absent synchronization |
| `boundary-or-encoding-mismatch` | API/DB/message/file serialization, dates, currency, IDs, enums | Producer format, incompatible consumer assumption, and corruptible value |
| `default-value-trap` | Falsy defaults, coercion, optional chaining, config fallbacks | Legitimate overridden input and resulting wrong behavior |
| `misleading-observability` | Health/readiness, logs, metrics, alerts, error reporting | Diagnostic claim and the dependency/failure it does not actually observe |
| `dependency-graph-shadow` | Direct imports, manifests, lockfiles, peers, production images | Runtime usage and missing/misclassified dependency plus concrete failure risk |
| `incomplete-lifecycle` | Connections, files, streams, listeners, timers, locks, temp files | Acquisition and reachable path where cleanup does not execute |
| `boundary-invariant-violation` | Assertions/casts, validators, shared types, ORM vs migrations | Declared invariant and concrete runtime data/schema mismatch |
| `git-history-risk` | Churn, patch stacking, stale TODOs, error-path changes, ownership | Historical signal combined with current reachable risk and weak protection |

## Execution

1. Select patterns from concrete repository surfaces; do not run syntax-only searches as findings.
2. Trace each signal across callers, boundaries, tests, configuration, or history.
3. Record clean/rejected investigations in coverage notes or the reject ledger.
4. Send plausible root causes to the universal promotion gate in `audit-rubric.md`.

Single-file findings remain valid standard candidates. A deep-analysis label never raises confidence or severity by itself.
