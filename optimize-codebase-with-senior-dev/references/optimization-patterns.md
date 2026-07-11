# Optimization Patterns

Use these patterns and anti-patterns when selecting or rejecting strategies.

## Contents

- Evidence and target isolation
- Ecosystem-native adoption
- Runtime, I/O, build, test, and CI patterns
- Complexity and navigation patterns
- Anti-patterns

## Patterns

### Measure Before Changing

Record the workflow, command, workload, environment, raw result, variance, and confidence before editing.

### Isolate the Hot Path

Trace the pain to the smallest code path, query, render loop, build phase, test group, or CI job that explains it.

### Inventory Before Recommending

Confirm the framework, resolved package version, plugins, configuration, runtime mode, and deployment target before applying ecosystem advice.

### Configure Before Adding

Check whether an existing runtime, framework, direct dependency, or tool already provides the required capability. Prefer a focused configuration change when it is supported, observable, and reversible.

### Use Version-Matched Evidence

Match official documentation to the resolved version or supported version range. When docs are ambiguous, inspect local types, metadata, source, changelog, or tests and lower confidence.

### Prefer Native Capabilities With Semantic Fit

Use framework-native rendering, data loading, caching, compilation, querying, scheduling, or deployment features only when they preserve required semantics and improve the named workflow.

### Replace Duplicate Machinery Carefully

Remove custom wrappers or utilities only after identifying every behavior they encode and proving the native capability covers required error, ordering, retry, auth, observability, and lifecycle semantics.

### Keep Dependencies Explicit

Do not import a transitive dependency as if it were stable API. Declare it only when ownership, versioning, security, bundle/runtime cost, and update policy are accepted.

### Cache Only With an Invalidation Story

Define key, lifetime, invalidation, stale behavior, memory/storage cost, failure mode, and verification before caching.

### Batch Repeated I/O

Combine repeated database, filesystem, network, or process calls while preserving ordering, partial failure, timeout, retry, and error-reporting semantics.

### Avoid Unnecessary Network Calls

Remove duplicate requests, prefetch only when useful, and preserve freshness, auth, cache-control, cancellation, and retry behavior.

### Reduce Duplicate Build and Test Work

Use supported incremental modes, task graphs, caches, dependency-aware selection, shared setup, and artifact reuse while preserving coverage and clear failures.

### Split CI for Feedback, Not Appearance

Parallelize independent work when it improves critical-path feedback. Account for duplicated setup, queue time, resource limits, and failure visibility.

### Prefer Incremental Adoption

Prove a framework or tooling capability on the smallest representative path before repo-wide adoption.

### Remove Dead Complexity With Coverage

Delete dead paths, compatibility branches, dependencies, or duplicate logic only when source evidence and tests preserve behavior.

### Simplify Before Abstracting

Consolidate duplicated policy and clarify ownership before introducing interfaces, registries, adapters, or plugin systems.

### Improve Agent Navigation When It Is the Target

Add concise repo maps, command guides, or subsystem notes when repeated navigation cost is evidenced. Keep them close to the workflow and verify them against code.

## Anti-Patterns

### Rewrite Everything

Broad rewrites increase review cost and regression risk before proving value.

### Upgrade Everything

Version churn is not optimization. Upgrade only for a concrete capability or fix that applies locally and can be verified.

### Follow Latest Docs Blindly

Advice for a newer major version, different router/runtime mode, or missing plugin is not evidence for the installed stack.

### Treat Installed as Useful

An installed package may be unused, duplicated, transitive, costly, insecure, or wrong for the target. Inventory is not endorsement.

### Add a Package for Every Problem

A dependency that saves a few lines can increase bundle size, startup, security surface, update work, and conceptual load.

### Depend on Transitive APIs

Importing an undeclared transitive package creates accidental compatibility and ownership risk.

### Introduce Caching Without Invalidation

Caching without freshness rules trades visible slowness for hidden correctness failures.

### Add Concurrency Without Semantics

Parallelism without ordering, backpressure, cancellation, resource bounds, and partial-failure design can make the workflow faster and less correct.

### Delete Tests or Hide Errors

Removing coverage or suppressing warnings, types, lint, validation, and failures makes the feedback loop less trustworthy.

### Add Hypothetical Abstractions

Future-proofing without a current leverage point increases complexity without measurable benefit.

### Benchmark the Wrong Workflow

An unrelated command, microbenchmark, or tiny fixture cannot prove improvement to the user's workflow.

### Claim Wins Without Comparable Evidence

Report raw before/after values, variance, workload, and environment. Treat inconclusive results as inconclusive.

### Bundle Unrelated Optimizations

Separate candidates so each can be reviewed, measured, reverted, and learned from.
