# Change Propagation Protocol

Use this for every function, type, constant, interface, route, schema, command, or shared helper the plan modifies.

## Trace

1. Search for all direct references: importers, callers, type annotations, tests, fixtures, docs, and snapshots.
2. Trace transitive callers: if a helper changes signature or behavior, inspect callers of its callers until the public boundary is clear.
3. Check test coverage: identify which tests exercise the changed code path and which gaps must be filled.
4. Check config surfaces: env vars, feature flags, generated clients, build scripts, migrations, schemas, and deployment hooks.

Use `rg` first. Prefer exact symbol searches, then broader path or string searches.

## Output Format

Standard and High-risk plans must include a Change Propagation Map:

```text
Changed Symbol -> [files that must be updated]
  - direct caller: src/orders/service.ts:31 - update required: yes - reason: signature gains required options
  - transitive caller: src/orders/route.ts:18 - update required: no - reason: service wrapper keeps route contract
  - test: tests/orders/service.test.ts:44 - update required: yes - reason: add assertion for missing status
```

Use `->` or `→`. Include file references with line numbers when possible.

## Completion Rule

If any file in the propagation map requires an update that the plan does not include, the plan is incomplete.

If a symbol has no references, state the exact search that proved it:

```text
Changed Symbol -> no direct references
  - search: `rg "normalizeOrderStatus" src tests` returned no matches beyond definition
```
