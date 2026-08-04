# Refactor the shared normalization helper

<!-- plan-contract: 7 -->
<!-- plan-metadata: {"intent":"refactor","tier":"standard","risk_domains":[]} -->

## Outcome
SC-1: given: consumer callers and the package re-export | when: normalization routes through the helper seam | then: both surfaces produce identical normalized output | unchanged: the normalized output remains stable

## Obligations
RQ-1: source: request | anchor: Refactor the shared name normalization helper | obligation: both consumers and the re-export must route through the helper seam | covered_by: SC-1, CH-1

## Evidence
F-1: kind: source | path: src/lib/core.py | lines: 1-2 | anchor: normalize | claim: normalize owns the shared normalization behavior
F-2: kind: source | path: src/consumer_a.py | lines: 1-3 | anchor: normalize | claim: the consumer imports the normalization seam

## Implementation
CH-1: path: src/lib/core.py | anchor: normalize | status: existing | evidence: F-1 | depends_on: none | change: move normalization behind the helper seam while preserving the exact normalized output | locality: shared | reversibility: reversible
CH-2: path: src/consumer_a.py | anchor: normalize | status: existing | evidence: F-2 | depends_on: none | change: route the consumer through the new helper seam call | locality: local | reversibility: reversible | propagation: local

## Propagation
P-1: surface: consumer | disposition: changed | path: src/consumer_a.py | owner: CH-1 | reason: F-1
P-2: surface: consumer | disposition: changed | path: src/lib/__init__.py | owner: CH-1 | reason: F-1

## Verification
T-1: covers: SC-1, CH-1, CH-2 | given: consumer and re-export callers | when: the targeted refactor tests execute | then: both surfaces produce identical normalized output | command: python -m pytest tests/test_refactor.py -q
