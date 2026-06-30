# Grilling Protocol

Use this when a plan or design needs pressure-testing before implementation. The goal is shared understanding of the plan, domain terms, key concepts, cited references, and relevant context, not a large transcript of questions.

## Design Tree Walk

1. State the current hypothesis in one paragraph.
2. Identify the root decision that determines the next branch.
3. Ask one question at a time.
4. Provide a recommended answer and the reason for it.
5. After the user answers, update the hypothesis and move to the next dependent decision.
6. Stop when each branch has an owner decision, a repo-backed default, or an explicit out-of-scope call.

## Context and Reference Alignment

Before treating the plan as understood, clarify:

- Canonical terms and rejected synonyms.
- Concept boundaries, relationships, and ownership.
- Referenced docs, tickets, APIs, schemas, prior decisions, or external context that affect the plan.
- Whether the user and repo use the same language for the same ideas.

If a referenced artifact cannot be checked, mark the dependent claim as an assumption and decide whether it blocks the plan.

## Pressure Tests

For each major decision, test at least one concrete scenario:

- Happy path with realistic data.
- Boundary case: empty, missing, duplicate, stale, oversized, or invalid data.
- Failure case: dependency unavailable, permission denied, validation failed, race, or rollback.
- Compatibility case: old clients, existing data, old configs, or previous behavior.

Prefer scenarios that force a boundary between two domain concepts or two architectural responsibilities.

## Assumption Handling

- Name the assumption.
- Classify it as product, technical, domain, migration, or test assumption.
- Decide whether it is blocking.
- If non-blocking, record the default and why it is safe.
- If blocking, ask the narrowest question that resolves it.

## Domain Docs Alignment

When business language appears:

- Check `CONTEXT.md` and `CONTEXT-MAP.md` before accepting new terms.
- If the user uses a term differently from the glossary, call out the conflict.
- Propose one canonical term for overloaded language.
- Keep glossary updates glossary-only: term, definition, aliases, and rejected meanings.
- Suggest an ADR only for hard-to-reverse, surprising, tradeoff-driven decisions.

## Shared-Understanding Exit Criteria

The grilling session is done when:

- Goal and success criteria are concrete.
- Important terms have agreed meanings.
- Important concepts have clear boundaries.
- Referenced docs or prior decisions have been checked or marked as assumptions.
- Context that affects the plan is explicitly captured.
- In-scope and out-of-scope behavior are named.
- Public interfaces and data shapes are decided or explicitly unchanged.
- Edge cases have expected behavior.
- Migration, compatibility, rollback, and docs decisions are settled when relevant.
- The test strategy proves the risky behavior.

If any item remains unresolved and matters to implementation, do not finalize the plan.
