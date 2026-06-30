# Anti-Patterns

Use this list when a plan feels plausible but weak. Fix the anti-pattern before finalizing.

## Premature Planning

Symptom: the plan starts from generic architecture instead of repo evidence.

Fix: read the entrypoint, call path, analogous implementation, and tests. Replace guesses with cited facts.

## Asking Discoverable Facts

Symptom: asking the user where files live, what framework is used, how tests run, or what the current schema looks like.

Fix: search and inspect first. Ask only when multiple repo-backed interpretations remain.

## Vague Final Plan

Symptom: phrases like "update relevant files", "handle edge cases", "ensure tests pass", or "wire this into the service".

Fix: name the behavior, interface, edge cases, and verification command. Keep file names only where needed to remove ambiguity.

## Generic Title

Symptom: the plan starts with "Implementation Plan", "Feature Plan", "Bug Fix Plan", or another title that names the document type instead of the actual change.

Fix: use a specific H1 title that names the behavior or system being changed, such as `# Add Order Export Status`.

## Deferred Decisions

Symptom: phrases like "during implementation", "choose the appropriate", "finalize later", or "API details later".

Fix: make the decision in the plan or ask the blocking question before finalizing. The plan-shape checker intentionally fails these phrases because they leave implementation choices unresolved.

## Over-Abstraction

Symptom: inventing providers, factories, adapters, registries, or shared interfaces before the repo needs them.

Fix: follow the existing local pattern. Add abstraction only when it removes real duplication, supports two concrete cases, or matches established architecture.

## Fake Certainty

Symptom: presenting assumptions as facts or ignoring contradictions between request, code, tests, and docs.

Fix: label assumptions, cite facts, and surface contradictions as decisions.

## Bloated Plans

Symptom: the plan lists every file, repeats obvious mechanics, or includes rollout and migration detail for a local reversible change.

Fix: choose the task tier. Include only detail that prevents likely implementation mistakes.

## Under-Specified Interfaces

Symptom: implementation steps mention changing an API, schema, command, event, type, or output without defining the new shape.

Fix: specify the public surface enough that implementers will not invent incompatible versions.

## Test Theater

Symptom: tests are listed by category but not tied to behavior or risk.

Fix: state the scenarios, existing test pattern to follow, exact command, and expected result.

## Rubric Theater

Symptom: the plan has the right headings but no repo evidence, expected results, rollback detail, or concrete assumptions.

Fix: run `scripts/check_plan_rubric.py` and tighten each failed section until it proves implementation readiness.

## Unverified Delegation

Symptom: treating a subagent summary as fact, or delegating broad synthesis such as "understand the whole repo" or "decide the architecture".

Fix: delegate only bounded evidence-gathering tasks. Require `file:line` citations, then spot-check the cited files before using the findings in the plan.

## Documentation Dumping

Symptom: putting implementation plans, file paths, API details, or acceptance criteria into `CONTEXT.md`.

Fix: keep `CONTEXT.md` glossary-only. Use ADRs only for durable tradeoffs that are hard to reverse and surprising without context.
