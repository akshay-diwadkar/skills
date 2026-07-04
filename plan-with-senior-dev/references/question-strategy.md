# Question Strategy

Ask questions to remove decisions, not to transfer research work to the user. Every question should change scope, behavior, architecture, risk, docs, or tests.

## Ask Only After Exploration

Before asking, verify whether code, tests, docs, config, schema, or established patterns already answer the question. If they do, use the discovered answer and cite it. If they do not, ask the narrowest blocking question and present it as explicit options.

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

Use this structure for blocking questions:

```text
Question: [specific decision]
Options:
- [Option 1] (Recommended) - [repo-backed default or concrete risk]
- [Option 2] - [tradeoff]
- [Option 3] - [tradeoff]
Why it matters: [what changes if the answer differs]
```

Use 2-4 mutually exclusive options. The recommended option must be a real recommendation, not a neutral restatement. If there is only one real answer, do not ask; record the repo-backed default or a conservative assumption instead.

## Blocking vs Non-Blocking

Blocking questions prevent a decision-complete plan. Ask and wait, but only after presenting options.

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
