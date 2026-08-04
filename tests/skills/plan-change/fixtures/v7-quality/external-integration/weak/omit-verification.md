# Add idempotent payment calls

<!-- plan-contract: 7 -->
<!-- plan-metadata: {"intent":"feature","tier":"standard","risk_domains":["external-integration"]} -->

## Outcome
SC-1: given: an ambiguous external payment response | when: charge retries the call | then: the retry is exact once under the idempotency key | unchanged: successful charges remain single

## Obligations
RQ-1: source: request | anchor: Add an idempotency key to external payment calls | obligation: ambiguous success must retry exactly once and never double-charge | covered_by: SC-1, CH-1

## Evidence
F-1: kind: external-call | path: src/billing.py | lines: 1-4 | anchor: charge | claim: charge owns the external payment call | callee: charge_request

## Implementation
CH-1: path: src/billing.py | anchor: charge | status: existing | evidence: F-1 | depends_on: none | change: send the idempotency key on every external payment call and retry ambiguous responses exactly once | locality: shared | reversibility: reversible

## Propagation
P-1: surface: contract | disposition: changed | path: src/billing.py | owner: CH-1 | reason: F-1

## Boundaries and Risks
B-1: class: provider success boundary | evidence: F-1 | flow: payment call -> ambiguous provider response -> exact-once retry
R-1: severity: P1 | owner: CH-1 | tests: T-1 | risk: ambiguous success could double-charge the customer

## Verification
T-1: covers: SC-1, CH-1 | given: success, ambiguous, and timeout provider responses | when: the targeted billing tests execute | then: the suite executes and reports a passing result | command: python -m pytest tests/test_billing.py -q

## Rollout and Rollback
Deploy the idempotency key in batches with per-merchant limits; when duplicate-charge evidence appears, disable retries and reconcile via the provider ledger.
