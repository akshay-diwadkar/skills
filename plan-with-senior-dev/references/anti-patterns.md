# Anti-Patterns

Use this list when a plan feels plausible but weak. Fix the anti-pattern before finalizing.

## Shallow Reasoning

Symptom: the plan jumps to a solution without decomposing the problem, identifying root cause, or rejecting alternatives.

Fix: run the Reason gate. Decompose, map dependencies, enumerate constraints, compare 2-3 approaches, and choose the smallest valid one.

## Missing Propagation

Symptom: the plan changes a function, type, constant, interface, schema, command, or helper without tracing all callers and tests.

Fix: run `rg` for direct references, trace transitive callers to the public boundary, and add a Change Propagation Map.

## Constraint Blindness

Symptom: the plan changes behavior without enumerating contracts, invariants, data rules, performance, security, compatibility, or business rules.

Fix: add Constraint Verification and mark each constraint preserved, modified, or at risk with evidence.

## Optimistic Implementation

Symptom: the plan assumes the happy path and does not attack edge cases, dependency surprises, partial failures, ordering, or scale.

Fix: run Devil's Advocate and modify the plan for P0/P1 findings.

## Signature Guessing

Symptom: the plan specifies function signatures, schemas, or public contracts without checking existing types and interfaces.

Fix: cite the existing signature or schema before proposing the new one.

## Premature Planning

Symptom: the plan starts from generic architecture instead of repo evidence.

Fix: read the entrypoint, call path, analogous implementation, tests, and config. Replace guesses with cited facts.

## Asking Discoverable Facts

Symptom: asking the user where files live, what framework is used, how tests run, or what the current schema looks like.

Fix: search and inspect first. Ask only when multiple repo-backed interpretations remain.

## Vague Final Plan

Symptom: phrases like "update relevant files", "handle edge cases", "ensure tests pass", or "wire this into the service".

Fix: name exact behavior, signatures, branches, edge cases, assertions, and verification commands.

## Generic Title

Symptom: the plan starts with "Implementation Plan", "Feature Plan", "Bug Fix Plan", or another title that names the document type instead of the actual change.

Fix: use a specific H1 title that names the behavior or system being changed.

## Deferred Decisions

Symptom: phrases like "during implementation", "choose the appropriate", "finalize later", or "API details later".

Fix: make the decision in the plan or ask the blocking question before finalizing.

## Over-Abstraction

Symptom: inventing providers, factories, adapters, registries, or shared interfaces before the repo needs them.

Fix: follow the existing local pattern. Add abstraction only when it removes real duplication, supports two concrete cases, or matches established architecture.

## Test Theater

Symptom: tests are listed by category but not tied to behavior or risk.

Fix: state exact inputs, outputs, assertions, existing test pattern, command, and expected result.

## Rubric Theater

Symptom: the plan has the right headings but no repo evidence, propagation map, constraints, pseudo-code, attack findings, or concrete assumptions.

Fix: run `scripts/check_plan.py` and tighten each failed section until it proves implementation readiness.

## Documentation Dumping

Symptom: putting implementation plans, file paths, API details, or acceptance criteria into `CONTEXT.md`.

Fix: keep `CONTEXT.md` glossary-only. Use ADRs only for durable tradeoffs that are hard to reverse and surprising without context.
