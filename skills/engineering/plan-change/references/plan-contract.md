# Plan contract v7

Required sections once in order; conditional sections only at shown positions.

```markdown
# <Action-oriented title>

<!-- plan-contract: 7 -->
<!-- plan-metadata: {"intent":"feature|bug-fix|refactor|migration|operational","tier":"tiny|standard|high-risk","risk_domains":[]} -->

## Obligations
RQ-1: source: request|audit|design|optimization|issue | category: <typed category when required> | anchor: <exact request/handoff text> | obligation: <material requirement> | covered_by: SC-1, CH-1

## Outcome
SC-1: given: <setup> | when: <action> | then: <result> | unchanged: <preserved behavior>

## Evidence
F-1: kind: source | path: <path> | lines: <start-end> | anchor: <exact text> | claim: <fact>

## Decisions
D-1: selected: <approach> | evidence: F-1 | rejected: <alternative> | drawback: <tradeoff>

## Implementation
CH-1: path: <path> | anchor: <seam> | status: existing|new | evidence: F-1 | change: <behavior> | depends_on: none|CH-n[,CH-n...] | locality: local|shared|test-only | reversibility: reversible|conditional|irreversible

## Propagation
P-1: surface: <caller|consumer|test|fixture|contract|config|schema|generated|deployment|documentation> | disposition: changed|test-only|unchanged|out-of-scope | path: <path> | owner: CH-1 | reason: <F ref or scope reason>

## Boundaries and Risks
B-1: class: <boundary> | evidence: F-1 | flow: <a -> b -> c>
R-1: severity: P0|P1|P2 | owner: CH-1 | tests: T-1 | risk: <failure mode>

## Verification
T-1: covers: SC-1, CH-1 | given: <setup> | when: <action> | then: <expectation> | command: <command>

## Rollout and Rollback
Deploy <change> in <order>. If <trigger>, roll back by <action> or roll forward by <action>.
```

Always include Obligations, Outcome, Evidence, Implementation, Verification.
Omit empty conditional sections. Records use positive IDs, `: ` after names, and
exact ` | ` separators. Existing CH need same-path evidence; new CH use
`owner: F-n|CH-n` resolving to `directory-ownership` or `generated-from`.

Each RQ covers ≥1 SC and ≥1 CH or T. Typed handoffs require RQ categories for the
handoff kind (design: decision+constraint; optimization: candidate+workflow+measure;
issue: outcome+protected-behavior+constraint) with anchors from selected handoff
material. Every SC/CH appears in some T.covers. Every CH declares depends_on,
locality, and reversibility. Shared CH need matching P on a distinct path or an
evidence-backed unchanged/out-of-scope declaration; P.surface must use the documented
enum. Non-tiny local CH need an evidence-backed no-propagation P (`unchanged` or
`out-of-scope` citing F-n). Changed/test-only P paths must exist or match a planned
CH path. Irreversible CH force high-risk, risks, and rollout. Bug-fix plans require
one T that states fail-before and after-the-fix pass expectations. Public-contract,
durable-state, migration, external-integration, and irreversible-effect domains
also need rollout with order, recovery action, and trigger.

The sealer verifies RQ anchors against loaded request/handoff bytes, validates
the CH graph, and adds plan-proof/plan-validation; never write those markers.

Tiny plans use Obligations plus the four core sections. Add Decisions/
Propagation for real choices, shared surfaces, or non-tiny local no-propagation
declarations.
