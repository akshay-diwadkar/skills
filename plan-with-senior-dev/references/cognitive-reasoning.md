# Cognitive Reasoning Protocol

Run this during the Reason gate before writing implementation steps. The output can be compact, but the thinking must happen in order.

## Step 1: Decompose

Break the problem into atomic sub-problems. Each sub-problem must have:

- One responsibility.
- Clear inputs and outputs.
- Identifiable constraints.
- Known unknowns.

If a sub-problem cannot be stated this way, explore more or ask one blocking question.

## Step 2: Root Cause Analysis

For bug fixes and refactors, trace symptoms to root cause with repo evidence. Use 5 Whys, but stop when the next why is speculation.

```text
Symptom: [observed failure]
Why 1: [repo-backed cause]
Why 2: [repo-backed deeper cause]
Root cause: [smallest cause the plan must fix]
Rejected symptom fix: [patch that would hide the symptom]
```

Never plan a fix that only masks the symptom unless the user explicitly asks for containment and the plan labels it as such.

## Step 3: Dependency Mapping

Build the affected dependency graph:

- Direct dependencies: imports, calls, type references, components, routes, jobs, and schemas.
- Transitive dependencies: callers of callers and downstream consumers.
- Test dependencies: tests, fixtures, snapshots, mocks, or contract tests exercising the path.
- Config dependencies: env vars, feature flags, generated files, build scripts, migrations, and deployment hooks.

Record contradictions: places where source, tests, docs, or config imply different behavior.

## Step 4: Constraint Identification

Enumerate constraints before choosing the solution:

- Type contracts: signatures, interfaces, schemas, generated clients.
- Data invariants: validation rules, state machines, uniqueness, nullability, serialization.
- Performance bounds: hot paths, pagination, batching, indexes, memory.
- Security constraints: auth, permissions, input validation, secrets, tenant isolation.
- Compatibility constraints: API contracts, data format versions, old/new clients.
- Business rules: domain logic, legal or regulatory requirements, product rules.

Classify each as preserved, modified, or at risk.

## Step 5: Solution Space Narrowing

Generate 2-3 candidate approaches, then eliminate any approach that:

- Violates an identified constraint.
- Requires broader change propagation than another valid approach.
- Diverges from existing repo patterns without a concrete benefit.
- Adds an abstraction before two concrete uses or local precedent justifies it.

State why the selected approach is the smallest correct approach.

## Step 6: Sequencing

Order the selected approach by dependency:

1. Foundation changes: types, schemas, interfaces, validation, migrations.
2. Core logic.
3. Public surface or orchestration.
4. Tests and fixtures.
5. Documentation and release notes.

If a later step requires an earlier step that the plan does not include, the plan is incomplete.
