# Question Strategy

Ask questions to remove decisions, not to transfer research work to the user. Every question should change scope, behavior, architecture, risk, docs, or tests.

## Ask Only After Exploration

Before asking, verify whether code, tests, docs, config, schema, or established patterns already answer the question. If they do, use the discovered answer and cite it.

Ask immediately only when the prompt itself is contradictory or impossible to interpret.

## Question Types

- Goal: what outcome matters to the user.
- Success criteria: what observable result proves the work is done.
- Scope: what is included, excluded, and intentionally unchanged.
- Public surface: API, schema, event, command, type, UI, file format, or output shape.
- Compatibility: migration, rollout, rollback, backwards compatibility, or data preservation.
- Domain language: canonical names and boundaries for overloaded business terms.
- Verification: acceptance tests, critical scenarios, and risk tolerance.

## Sequencing

1. Resolve blocking intent first: goal, audience, success criteria, and scope.
2. Resolve durable interfaces next: public contracts, schemas, migrations, and compatibility.
3. Resolve behavior edges: errors, permissions, empty states, concurrency, external failures, and rollback.
4. Resolve test expectations last, after behavior is clear.

Do not ask a long questionnaire when one blocking question controls the rest of the design tree.

## Recommended Format

Use this structure:

```text
Question: [specific decision]
Recommended answer: [default], because [repo evidence or concrete risk]
Why it matters: [what changes if the answer differs]
```

The recommended answer must be a real recommendation, not a neutral restatement.

## Blocking vs Non-Blocking

Blocking questions prevent a decision-complete plan. Ask and wait.

Non-blocking questions improve polish but do not affect core behavior. Record a conservative assumption and continue.

A question is blocking when the answer changes:

- User-visible behavior.
- Public contracts.
- Persisted data.
- Security, billing, permissions, or compliance behavior.
- Migration or rollback policy.
- Test strategy for high-risk behavior.

## When Not To Ask

- The repo already answers it.
- The answer is an implementation detail dictated by existing patterns.
- The choice is easy to reverse and not user-visible.
- The question is really a request for permission to do normal engineering work.
- The user already gave a success criterion that makes one option clearly correct.
