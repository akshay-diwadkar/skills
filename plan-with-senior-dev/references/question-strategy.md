# Question Strategy

Ask questions to remove decisions, not to transfer research work to the user. Every question must change scope, behavior, architecture, risk, docs, migrations, public contracts, or tests.

## Limits

- Ask at most two blocking questions per plan.
- If a third question seems necessary, first prove the repo cannot answer it with source, tests, docs, config, schema, or established patterns.
- Collapse lower-risk decisions into conservative, repo-backed assumptions instead of asking.
- Ask immediately only when the prompt is contradictory or impossible to interpret.

## Ask Only After Exploration

Before asking, verify whether the repo already answers the question. If it does, use the discovered answer and cite it. If it does not, ask the narrowest blocking question and include a recommendation.

## Question Types

- Goal: what outcome matters.
- Success criteria: what observable result proves completion.
- Scope: included, excluded, intentionally unchanged.
- Public surface: API, schema, event, command, type, UI, file format, or output shape.
- Compatibility: migration, rollout, rollback, data preservation.
- Domain language: canonical names and boundaries for overloaded terms.
- Verification: acceptance tests, risk tolerance, critical scenarios.

## Sequencing

1. Resolve blocking intent first: goal, audience, success criteria, and scope.
2. Resolve durable interfaces next: public contracts, schemas, migrations, compatibility.
3. Resolve behavior edges: errors, permissions, empty states, concurrency, external failures, rollback.
4. Resolve test expectations last, after behavior is clear.

## Required Format

```text
Question: [specific decision]
Recommendation: [one concrete option] because [repo evidence or risk].
Options:
- [Option 1] (Recommended) - [repo-backed default or concrete risk]
- [Option 2] - [tradeoff]
- [Option 3] - [tradeoff]
Why it matters: [what changes if the answer differs]
```

Use 2-4 mutually exclusive options. The recommended option must be a real recommendation, not a neutral restatement.

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
- Existing patterns dictate the implementation detail.
- The choice is easy to reverse and not user-visible.
- The question is a request for permission to do normal engineering work.
- The user already gave a success criterion that makes one option clearly correct.
