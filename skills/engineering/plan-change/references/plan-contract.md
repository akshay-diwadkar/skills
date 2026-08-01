# Plan contract v6

Use required sections once in this order; insert conditional sections only at
the shown positions.

```markdown
# <Action-oriented title>

<!-- plan-contract: 6 -->
<!-- plan-metadata: {"intent":"feature|bug-fix|refactor","tier":"tiny|standard|high-risk","risk_domains":[]} -->

## Outcome
SC-1: given: <observable setup> | when: <named action> | then: <observable result> | unchanged: <preserved behavior>

## Evidence
F-1: kind: source | path: <repo-relative file> | lines: <start-end> | anchor: <exact text> | claim: <plan-relevant fact>

## Decisions
D-1: selected: <approach> | evidence: F-1 | rejected: <alternative> | drawback: <tradeoff>

## Implementation
CH-1: path: <repo-relative path> | anchor: <existing anchor or ownership seam> | status: existing|new | evidence: F-1 | change: <literal behavior> | locality: local|shared|test-only | reversibility: reversible|conditional|irreversible

## Propagation
P-1: surface: <caller|consumer|test|fixture|contract|config|schema|generated|deployment|documentation> | disposition: changed|test-only|unchanged|out-of-scope | path: <path or F reference> | owner: CH-1 | reason: <F reference or concrete scope reason>

## Boundaries and Risks
B-1: class: <boundary> | evidence: F-1 | flow: <stage one -> stage two -> stage three>
R-1: severity: P0|P1|P2 | owner: CH-1 | tests: T-1 | risk: <specific failure mode>

## Verification
T-1: covers: SC-1, CH-1 | given: <setup> | when: <action> | then: <exact expectation> | command: <targeted runnable command>

## Rollout and Rollback
Deploy <named change> in <explicit order or bounded phases>. If <observable
trigger or condition>, roll back by <specific action> or roll forward by
<specific action>.
```

Always include Outcome, Evidence, Implementation, and Verification. Omit empty
conditional sections; blank, placeholder-only, or deferred sections are invalid.
Every record uses a positive integer ID, `: ` after the ID and each field name,
and exact ` | ` field separators. Existing changes require same-path evidence. New changes
omit `evidence` only when no existing target exists and instead include
`owner: F-n|CH-n`; an owning fact must be `directory-ownership` or
`generated-from`.

Every `SC` and `CH` must appear in at least one `T.covers`. High-risk plans need
at least one `B` and `R`. Public-contract, durable-state, migration,
external-integration, and irreversible-effect domains also need rollout and
rollback. That section must name substantive deployment ordering, a rollback or
roll-forward action, and the observable condition that triggers it.

The sealer adds `plan-proof` and `plan-validation`; never write them manually.

## Compact examples

Tiny plans use only the four required sections. A standard shared refactor adds
`Decisions` and `Propagation` only when exploration identifies a real choice or
consumer. In both cases, keep evidence to the smallest ranges that prove
material implementation claims.
