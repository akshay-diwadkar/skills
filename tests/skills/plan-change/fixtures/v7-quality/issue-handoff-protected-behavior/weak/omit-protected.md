# Add telemetry to silent skips

<!-- plan-contract: 7 -->
<!-- plan-metadata: {"intent":"feature","tier":"standard","risk_domains":[]} -->

## Outcome
SC-1: given: a feature flag that is off | when: run resolves the mode | then: it stays silent and only records telemetry | unchanged: the auth cache stays warm

## Obligations
RQ-1: source: handoff | anchor: Preserve silent skip behavior | obligation: the skip behavior must remain silent and only add telemetry | covered_by: SC-1, CH-1

## Evidence
F-1: kind: source | path: src/skip.py | lines: 1-4 | anchor: run | claim: run owns the skip and telemetry decision

## Implementation
CH-1: path: src/skip.py | anchor: run | status: existing | evidence: F-1 | depends_on: none | change: record telemetry for silent skips without changing the returned skip result | locality: local | reversibility: reversible | propagation: local

## Verification
T-1: covers: SC-1, CH-1 | given: flag-off and flag-on modes | when: the targeted skip tests execute | then: flag-off stays silent and telemetry records once | command: python -m pytest tests/test_skip.py -q
