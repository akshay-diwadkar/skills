# Fix absent target input

<!-- plan-contract: 7 -->
<!-- plan-metadata: {"intent":"bug-fix","tier":"tiny","risk_domains":[]} -->

## Outcome
SC-1: given: an absent target input | when: target processes the value | then: it returns an empty string | unchanged: present values remain stripped

## Obligations
RQ-1: source: request | anchor: Fix absent target input | obligation: an absent target input must produce an empty string | covered_by: SC-1, CH-1

## Evidence
F-1: kind: source | path: src/util.py | lines: 1-2 | anchor: util | claim: util owns absent-value handling

## Implementation
CH-1: path: src/target.py | anchor: target | status: existing | evidence: F-1 | depends_on: none | change: return the empty string for absent values before stripping present names | locality: local | reversibility: reversible | propagation: local

## Verification
T-1: covers: SC-1, CH-1 | given: absent and present input cases | when: the targeted target tests execute | then: absent input is empty and present input is stripped | command: python -m pytest tests/test_target.py -q
