# Make the job claim idempotent

<!-- plan-contract: 7 -->
<!-- plan-metadata: {"intent":"operational","tier":"standard","risk_domains":["durable-state"]} -->

## Outcome
SC-1: given: duplicate concurrent claims | when: claim_job resolves ownership | then: exactly one worker owns the job | unchanged: sequential claim outcomes remain stable

## Obligations
RQ-1: source: request | anchor: Make the job claim idempotent | obligation: duplicate concurrent claims must converge to one owned execution | covered_by: SC-1, CH-1

## Evidence
F-1: kind: source | path: src/queue.py | lines: 1-8 | anchor: claim_job | claim: claim_job owns claim resolution

## Implementation
CH-1: path: src/queue.py | anchor: claim_job | status: existing | evidence: F-1 | depends_on: none | change: resolve duplicate concurrent claims through the idempotent claim record | locality: shared | reversibility: reversible

## Propagation
P-1: surface: contract | disposition: changed | path: src/queue.py | owner: CH-1 | reason: F-1

## Boundaries and Risks
B-1: class: claim ownership boundary | evidence: F-1 | flow: duplicate claim -> idempotent record -> one owned execution

## Verification
T-1: covers: SC-1, CH-1 | given: sequential, duplicate, and concurrent claim inputs | when: the targeted queue tests execute | then: exactly one worker owns every job and outcomes stay stable | command: python -m pytest tests/test_queue.py -q

## Rollout and Rollback
Deploy idempotent claiming in phases behind a feature gate; when duplicate-execution evidence appears, revert to the prior claim path and retry owned jobs.
