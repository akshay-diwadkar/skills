# Plan contract v7

Use required sections once in this order; insert conditional sections only at
the shown positions.

```markdown
# <Action-oriented title>

<!-- plan-contract: 7 -->
<!-- plan-metadata: {"intent":"feature|bug-fix|refactor|migration|operational","tier":"tiny|standard|high-risk","risk_domains":[]} -->

## Outcome
SC-1: given: <observable setup> | when: <named action> | then: <observable result> | unchanged: <preserved behavior>

## Obligations
RQ-1: source: <request|handoff|issue> | anchor: <exact text from the request or handoff> | obligation: <restated obligation> | covered_by: SC-1, CH-1

## Evidence
F-1: kind: source | path: <repo-relative file> | lines: <start-end> | anchor: <exact text> | claim: <plan-relevant fact>

## Decisions
D-1: selected: <approach> | evidence: F-1 | rejected: <alternative> | drawback: <tradeoff>

## Implementation
CH-1: path: <repo-relative path> | anchor: <existing anchor or ownership seam> | status: existing|new | evidence: F-1 | depends_on: none|CH-n | change: <literal behavior> | locality: local|shared|test-only | reversibility: reversible|conditional|irreversible

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

Always include Outcome, Obligations, Evidence, Implementation, and
Verification. Omit empty conditional sections; blank, placeholder-only, or
deferred sections are invalid. Every record uses a positive integer ID, `: `
after the ID and each field name, and exact ` | ` field separators. Existing
changes require same-path evidence. New changes omit `evidence` only when no
existing target exists and instead include `owner: F-n|CH-n`; an owning fact
must be `directory-ownership` or `generated-from`.

Every `SC` and `CH` must appear in at least one `T.covers`. High-risk plans need
at least one `B` and `R`. Public-contract, durable-state, migration,
external-integration, and irreversible-effect domains also need rollout and
rollback. That section must name substantive deployment ordering, a rollback or
roll-forward action, and the observable condition that triggers it.

The sealer adds `plan-proof` and `plan-validation`; never write them manually.
The `plan-proof` and `plan-validation` markers are sealer-owned: the sealer
records the proof bundle, obligation anchors, bound files, and receipt digests
in exactly the shape it validates.

## Obligations

Every v7 plan binds its requests through `RQ` records. Each `RQ` restates one
obligation from the request or typed handoff, carries an `anchor` that must
appear verbatim in the request bytes, and `covered_by` links to at least one
success criterion (`SC`) and one implementation or verification record (`CH` or
`T`). The sealer rejects unknown, unreferenced, or circular coverage and any
anchor absent from the exact request. Obligation selection is agent-owned; the
sealer verifies anchors and coverage, it does not infer obligations.

## Change dependencies

Every `CH` declares `depends_on` as `none` or a list of `CH` references. The
sealer rejects dependencies on unknown changes, self-dependencies, and cycles,
and derives one deterministic dependency-ordered execution sequence for the
plan. `depends_on` expresses required ordering only; locality and reversibility
stay orthogonal.

## Propagation accounting

Shared changes (`locality: shared`) must carry a matching `P` record whose
`owner` references the change. Non-tiny plans must account every non-test-only
change either with a `P` record owned by the change or with an explicit
evidence-backed `propagation: local|none` declaration on the owning `CH`.
Irreversible changes (`reversibility: irreversible`) require the high-risk tier
and the `irreversible-external-effect` risk domain, which in turn requires a
concrete Rollout and Rollback section. Tiny plans are exempt from propagation
accounting to avoid template inflation; they still keep the four mandatory
sections and one `RQ` record.

## Compact examples

Tiny plans use the required sections plus `Obligations` and one `RQ` record. A
standard shared refactor adds `Decisions` and `Propagation` only when
exploration identifies a real choice or consumer. In both cases, keep evidence
to the smallest ranges that prove material implementation claims.
