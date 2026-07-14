# Deep Analysis Patterns

Use these patterns after the standard coverage matrix passes are complete. Each pattern targets a class of issue that is invisible in single-file review and requires cross-file, cross-boundary, or temporally-aware reasoning. Run these patterns using the risk map, ecosystem inventory, and repo frame already built by the audit protocol.

Deep analysis findings map to the existing category taxonomy. A single deep analysis finding may surface as a `bug`, `security`, `performance`, `test-gap`, `architecture`, `maintainability`, or `developer-experience` issue depending on its impact. The pattern that discovered it is metadata for the auditor, not a new category.

## 1. Semantic Contract Drift

Code evolves but callers and tests still assume the old contract.

### What to look for

- Functions whose return type, error behavior, nullability, or side effects changed, while call-sites still assume the previous contract.
- A function that used to return `null` on failure now throws, but callers still guard with `if (result === null)`.
- A method that used to be synchronous is now `async`, but some callers do not `await` it.
- An API endpoint that added a required field, but internal callers still omit it.
- Tests that assert on a shape, value, or error the function no longer produces.

### Where to look

- Functions with many callers across module boundaries.
- Interfaces, abstract classes, or protocol types with multiple implementors.
- Functions recently changed (use `git log` for recent modifications) that have callers in other modules.
- Shared utility modules imported by many packages.

### Evidence gate

Accept only when you can show both the changed contract (source diff, type change, or documented behavior shift) AND at least one concrete mismatched call-site or test. A changed function without a broken caller is not a finding.

---

## 2. Implicit Ordering Dependencies

Correctness depends on execution order but nothing enforces it.

### What to look for

- Initialization sequences where reordering statements would break behavior: module-level side effects, service registration, middleware chains, plugin loading.
- Database migration files whose correctness depends on prior migrations running in a specific order, but the ordering mechanism is fragile (filename sort, manual index).
- Event handler or subscription registration where the order of listeners determines priority, deduplication, or state.
- Configuration loading sequences where later steps depend on values set by earlier steps, but no dependency is declared.
- Import order that matters because of side effects (polyfills, monkey-patching, global registration).

### Where to look

- Application bootstrap and entry-point files.
- Middleware registration (Express, Koa, Django, ASP.NET, etc.).
- Migration directories and migration runner configuration.
- Event emitter setup, pub/sub subscription, and hook registration.
- Test setup and teardown files (especially `beforeAll`/`beforeEach` ordering).

### Evidence gate

Accept only when you can show two or more operations whose relative order matters AND no mechanism (explicit dependency declaration, topological sort, documented contract) enforces that order. Mere sequential code is not a finding; the risk is that a reasonable refactor could reorder it silently.

---

## 3. Error Swallowing & Silent Degradation

Errors are caught but not surfaced in a way any caller or operator can act on.

### What to look for

- Catch blocks that log but do not re-throw, return an error value, set an error state, or propagate the failure to any caller or monitoring system.
- Promise chains with `.catch(() => defaultValue)` or `.catch(() => {})` that mask failures behind valid-looking results.
- Error boundaries (React, framework-level catch-all middleware) that render a fallback but do not report the error or propagate it to the error tracking system.
- Retry logic that exhausts retries and then silently returns a stale or default value.
- Fallback branches that produce a valid response from stale or incomplete data without signaling degradation.
- Try/catch around critical operations (payment, auth, data mutation) where the catch path continues as if the operation succeeded.

### Where to look

- API route handlers and controller methods.
- Data fetching and caching layers.
- Background job and queue processing.
- Third-party service integration points.
- State management side effects (Redux sagas/thunks, Vuex actions, MobX reactions).

### Evidence gate

Accept only when you can show a catch, fallback, or error boundary that consumes an error from a path where the caller, user, or operator has no other way to learn the operation failed. Intentionally silent error handling with a clear comment or design rationale is a reject, not a finding. A catch that sets an error flag, emits a metric, or returns a typed error value is not swallowing.

---

## 4. Stale Cross-References & Phantom Dependencies

Symbols, configs, or resources are referenced from one side but missing from the other.

### What to look for

- Environment variables read in code (`process.env.X`, `os.environ["X"]`, `env("X")`) but not defined in any `.env`, `.env.example`, deployment config, or documentation.
- Environment variables defined in config but never read by any code.
- Feature flags checked in code but not defined in the flag management system, or defined but never checked.
- Route definitions pointing to handler functions, controllers, or views that no longer exist.
- CSS classes or IDs applied in templates/JSX but not defined in any stylesheet, CSS module, or utility framework config.
- CSS selectors defined in stylesheets but never applied in any template.
- Database table or column references in code that do not match the current schema or migrations.
- Configuration keys read by code that are absent from all config files and have no default.
- Import statements for modules, functions, or types that no longer exist at the referenced path.

### Where to look

- Application config loading and environment variable access patterns.
- Route/URL configuration files.
- Template and component files referencing CSS classes.
- ORM model definitions vs. migration files vs. query code.
- Feature flag evaluation sites vs. flag definition sources.

### Evidence gate

Accept only when you can show the reference on one side AND the missing definition or consumer on the other. A missing `.env.example` entry is a finding only if the code has no fallback and would fail or misbehave at runtime. Dead CSS that is clearly part of a component library or design system is a reject.

---

## 5. Temporal Coupling & Race Conditions

Operations that must be atomic or sequenced are neither.

### What to look for

- Read-modify-write sequences on shared state (database rows, in-memory caches, files, global variables) without locking, transactions, or compare-and-swap.
- Time-of-check-to-time-of-use (TOCTOU) in file system operations: checking existence then reading, checking permissions then acting.
- `async` functions called without `await`, causing the caller to proceed before the operation completes.
- State reads in event handlers or callbacks that assume a value set in a previous tick or lifecycle phase.
- Cache invalidation that runs after the response is sent, creating a window where stale data is served.
- Concurrent request handlers that share mutable module-level or class-level state.
- Database operations that assume sequential execution but run inside a concurrent request handler without transactions.

### Where to look

- Request handlers that read-then-write database records.
- Caching layers and cache invalidation logic.
- File system operations in CLI tools, build scripts, or server-side code.
- WebSocket or real-time event handlers with shared state.
- Background job processing with shared queues or state.
- Anywhere `async`/`await`, Promises, goroutines, threads, or callbacks interact with shared mutable state.

### Evidence gate

Accept only when you can show the shared mutable state AND the concurrent access path AND the absence of a synchronization mechanism. Single-threaded event-loop code with no concurrent entry points is not a race condition. Read-only access to shared state is not a finding.

---

## 6. Boundary & Encoding Mismatches

Data transforms incorrectly or loses fidelity when crossing system boundaries.

### What to look for

- Serialization/deserialization asymmetry: encoding with one method and decoding with another (e.g., `JSON.stringify` on one side, manual string splitting on the other; URL-encoding on write, no decoding on read).
- Character encoding assumptions at boundaries: code that assumes UTF-8 but reads from a source that may produce Latin-1 or Windows-1252 (database connections, file reads, HTTP responses without charset headers).
- Timezone handling inconsistencies: storing dates as local time in one component but interpreting as UTC in another; formatting with timezone but parsing without it; database columns that strip timezone info.
- Numeric precision loss: float-to-integer truncation across API boundaries, JavaScript `Number` precision loss for large integers from a 64-bit backend, currency calculations using floating point.
- Enum or status code mapping mismatches between systems: API returns new enum values that the client doesn't handle, database stores values the application code doesn't recognize.

### Where to look

- API request/response serialization and client-side deserialization.
- Database driver configuration and ORM serialization settings.
- File I/O operations, especially CSV/TSV parsing and generation.
- Inter-service communication (REST, gRPC, message queues).
- Frontend-backend data exchange for dates, currencies, and large IDs.

### Evidence gate

Accept only when you can show the encoding or format used on the producing side AND a different assumption on the consuming side AND a concrete data value or type that would be corrupted. Theoretical encoding mismatches without a plausible data path are a reject.

---

## 7. Default Value Traps

Fallback values that produce valid-but-wrong results silently.

### What to look for

- Logical OR (`||`) used for defaults where the value can legitimately be `0`, `""`, `false`, or `NaN`. The correct operator is usually nullish coalescing (`??`) or an explicit `undefined`/`null` check.
- Default function parameters that shadow explicitly passed `undefined` (in JavaScript, `f(undefined)` still triggers the default; this is sometimes intentional but often a bug when the caller meant "no value").
- Configuration defaults that were correct at project creation but are now wrong for the current deployment (e.g., `localhost` defaults in production-bound code, default page sizes that don't match the actual data volume).
- Boolean coercion traps: `if (value)` where `value` is a number, string, or array and `0`, `""`, or `[]` are valid inputs.
- Optional chaining (`?.`) that silently produces `undefined` where a missing value should be an error.

### Where to look

- Configuration loading and environment variable parsing.
- Function signatures with default parameters, especially in shared utilities.
- Data validation and normalization layers.
- CLI argument parsing.
- Query parameter and form data processing.

### Evidence gate

Accept only when you can show the default/fallback mechanism AND a legitimate input value that it would incorrectly discard or override AND the resulting incorrect behavior. A fallback for a value that is never legitimately falsy is not a finding.

---

## 8. Observability Gaps & Misleading Diagnostics

Monitoring, logging, and health checks that give false confidence.

### What to look for

- Health check endpoints that return 200/OK without verifying downstream dependencies (database, cache, external services) that the application requires to function.
- Log messages that reference variable names, function names, or module names that have been renamed, moved, or removed, making debugging misleading.
- Error messages that suggest a cause or fix that is no longer correct after code changes.
- Metrics that measure a proxy rather than the actual concern (e.g., counting enqueued items but not processing latency or failure rate).
- Structured logging that omits correlation IDs, request IDs, or user context, making it impossible to trace a request through the system.
- Alerting thresholds that reference absolute values from a previous scale and would not trigger at current traffic.
- Catch blocks that log a generic message ("Something went wrong") instead of the actual error, losing the stack trace and error type.

### Where to look

- Health check and readiness probe endpoints.
- Logging configuration and log statements in error paths.
- Metrics and instrumentation setup.
- Alerting and monitoring configuration.
- Error reporting integration (Sentry, Datadog, etc.).

### Evidence gate

Accept only when you can show the diagnostic mechanism AND the gap between what it claims to verify and what it actually verifies. A health check that intentionally omits a dependency check with a documented reason is a reject. A log message that is generic but includes the error object as a parameter is not "misleading."

---

## 9. Build & Dependency Graph Shadows

The dependency graph the tools see differs from the one the runtime uses.

### What to look for

- Transitive dependencies used directly in application code but not declared in the direct dependency manifest. The code works because another package pulls it in, but a dependency update or removal would break the build or runtime.
- `devDependencies` imported in production code paths. The application works locally and in CI but would fail in a production build that strips dev dependencies.
- Version ranges (`^`, `~`, `>=`) on dependencies with a history of breaking changes, where the lockfile is the only thing preventing a broken resolution.
- Circular dependencies between modules that work under the current bundler but would break under tree-shaking, code-splitting, or a bundler change.
- Lockfile that is committed but stale (last modified much earlier than `package.json` or equivalent, suggesting `install` wasn't re-run after a manifest change).
- Peer dependency requirements that are not satisfied by the project's direct dependencies.
- Multiple versions of the same package resolved in the lockfile (dependency duplication) causing bundle bloat or runtime inconsistency.

### Where to look

- `package.json`, `requirements.txt`, `Gemfile`, `go.mod`, `Cargo.toml`, and equivalent manifests.
- Lockfiles: `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `Pipfile.lock`, `Gemfile.lock`, `go.sum`, `Cargo.lock`.
- Import statements in production source code cross-referenced against the manifest.
- Bundler configuration and output analysis.
- CI build scripts and Docker build steps.

### Evidence gate

Accept only when you can show the import or usage in production code AND the dependency's absence from (or incorrect position in) the manifest. Transitive dependencies used only in test code are a lower-risk finding. Circular dependencies are a finding only if you can show a concrete bundler behavior or runtime ordering issue.

---

## 10. Incomplete Lifecycle Management

Resources acquired but not released on all code paths.

### What to look for

- Database connections, pools, or clients opened but not closed in error paths, early returns, or cancellation flows.
- File handles or streams opened but not closed when an exception occurs between open and close.
- Event listeners, subscriptions, or observers added but never removed, causing memory leaks or unintended side effects.
- `setInterval`, `setTimeout`, or framework-equivalent timers started but never cleared on teardown.
- UI component lifecycle asymmetry: effects or subscriptions set up in mount/init but not cleaned up in unmount/destroy (React `useEffect` without cleanup, Angular `ngOnInit` without `ngOnDestroy`, Vue `mounted` without `beforeUnmount`).
- Locks, semaphores, or mutex acquisitions without guaranteed release in a `finally` block or equivalent.
- Temporary files or directories created but not cleaned up on error.

### Where to look

- Database access layers and connection management.
- File and stream operations, especially in utilities and CLI tools.
- UI component lifecycle methods and hooks.
- Background worker and job processing code.
- Test setup and teardown (leaked resources between tests cause flakiness).
- Server startup and graceful shutdown handlers.

### Evidence gate

Accept only when you can show the resource acquisition AND a concrete code path (error, early return, cancellation, component unmount) where the release does not execute. Resources managed by a framework's lifecycle (e.g., a connection pool that auto-closes on process exit) require showing that the framework guarantee does not apply. A `finally` block or `using`/`with`/`defer` statement that covers the release is a reject.

---

## 11. Invariant Violations at Boundaries

The type system or validation says one thing but the runtime does another.

### What to look for

- Type assertions (`as`, `as unknown as T`, force-unwrap, unchecked casts) at module boundaries that bypass validation, allowing invalid data to enter a module that assumes it has been validated.
- API input validation that accepts a different shape than the internal type expects (e.g., the validator allows extra fields the type doesn't model, or the validator is more permissive than the downstream code assumes).
- Database schema assumptions in code (column types, NOT NULL constraints, foreign keys) that are not enforced by actual migrations or database constraints.
- API response types that promise a shape the backend does not always produce (e.g., a field typed as `string` that is actually `string | null` depending on state).
- Shared types between frontend and backend that have drifted (the generated or manually-maintained type no longer matches the actual API contract).
- Runtime type checks (`instanceof`, `typeof`, discriminated unions) that do not cover all cases the system can actually produce.

### Where to look

- API boundary layers: request handlers, middleware, response formatters.
- Shared type definitions used across packages or services.
- ORM model definitions vs. actual migration/schema files.
- Type assertion sites (grep for `as `, `as any`, `as unknown`, `!`, `@ts-ignore`, `# type: ignore`).
- Code generation outputs and their consumers.

### Evidence gate

Accept only when you can show the boundary assertion or type AND the concrete mismatch with the actual data that crosses the boundary. Type assertions inside a function that immediately validates the value are a reject. Typing `any` in test helpers or test fixtures is a reject unless it leaks into production code.

---

## 12. Git-History Signals

Version control history reveals structural risk the current snapshot does not.

### What to look for

- **Hotspot files**: files with high commit frequency (churn) that also have low or no test coverage. These are empirically the highest-risk files in a codebase.
- **Patch stacking**: functions or files that have been patched repeatedly in small incremental fixes, suggesting a deeper design issue that each patch works around rather than resolves.
- **Stale TODOs and FIXMEs**: comments tagged `TODO`, `FIXME`, `HACK`, `XXX`, or `WORKAROUND` with blame dates older than 6 months. If they were important enough to mark, the staleness itself is a maintainability signal.
- **Recent error-path changes**: error handling, catch blocks, or fallback logic modified in the last few releases without corresponding test additions.
- **Large uncommitted or unreviewed changes**: PRs or commits that touched many files without corresponding review or test changes (detectable from merge commit metadata).
- **Ownership gaps**: files or directories with no recent commits from any active contributor, suggesting abandoned or orphaned code.

### Where to look

- `git log --format='%H' -- <file> | wc -l` for churn counts.
- `git log --diff-filter=M --name-only` for recently modified files.
- `git blame` on TODO/FIXME lines for staleness.
- `git log --follow` on repeatedly-patched functions.
- Coverage reports cross-referenced with churn data.
- `git shortlog -sn -- <directory>` for ownership analysis.

### Evidence gate

Accept only when the git-history signal is combined with a concrete current-state risk. High churn alone is not a finding; high churn plus low coverage plus recent bug fixes IS a finding. A stale TODO is a finding only if the code it marks is still reachable and the concern it describes is still valid. Ownership gaps are a finding only if the orphaned code is in an active code path.

---

## Running the Deep Analysis Pass

After completing the standard coverage matrix passes, run the deep analysis patterns as follows:

1. **Select applicable patterns.** Not all 12 patterns apply to every codebase. Use the repo frame, ecosystem inventory, and risk map to select patterns that have plausible targets. Skip patterns that have no relevant surface (e.g., skip UI lifecycle management in a CLI tool, skip timezone boundary issues in a single-timezone batch processor).

2. **Run each selected pattern.** For each pattern, identify concrete investigation targets from the risk map, then inspect the source code, configuration, and (when applicable) git history for the pattern's signals. Record candidates in the candidate ledger with the pattern name as metadata.

3. **Apply the cross-file evidence requirement.** Deep analysis candidates must cite evidence from at least two files or two distinct system boundaries to be promoted. Single-file issues are already covered by the standard passes.

4. **Apply the standard rubric.** Deep analysis candidates pass or fail the same evidence gate, severity threshold, and confidence requirements as standard candidates. The pattern is not a shortcut past the rubric.

5. **Record rejects explicitly.** Patterns that were investigated but produced no findings get a reject entry in the reject ledger with the reason (e.g., "no cross-boundary serialization found" or "all async calls are awaited").
