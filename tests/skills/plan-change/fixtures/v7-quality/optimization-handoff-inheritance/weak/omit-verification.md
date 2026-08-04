# Hoist the recurring length computation

<!-- plan-contract: 7 -->
<!-- plan-metadata: {"intent":"refactor","tier":"standard","risk_domains":[]} -->

## Outcome
SC-1: given: scan over a value list | when: the optimized loop executes | then: the length computation is hoisted out of the loop | unchanged: per-iteration ordering and output remain stable

## Obligations
RQ-1: source: handoff | anchor: hoist the recurring length computation | obligation: the recurring length computation must move out of the loop | covered_by: SC-1, CH-1

## Evidence
F-1: kind: source | path: src/scan.py | lines: 1-7 | anchor: scan | claim: scan owns the recurring length computation

## Implementation
CH-1: path: src/scan.py | anchor: scan | status: existing | evidence: F-1 | depends_on: none | change: hoist the length computation out of the loop while preserving per-iteration ordering | locality: local | reversibility: reversible | propagation: local

## Verification
T-1: covers: SC-1, CH-1 | given: ordered and unordered value lists | when: the targeted scan tests execute | then: the suite executes and reports a passing result | command: python -m pytest tests/test_scan.py -q
