# Fix absent-name normalization

<!-- plan-contract: 7 -->
<!-- plan-metadata: {"intent":"bug-fix","tier":"standard","risk_domains":[]} -->

## Outcome
SC-1: given: an absent input name | when: normalize_name handles the value | then: it returns an empty string | unchanged: present names remain normalized

## Obligations
RQ-1: source: handoff | anchor: Fix absent-name normalization | obligation: absent input names must normalize to an empty string | covered_by: SC-1, CH-1

## Evidence
F-1: kind: source | path: src/names.py | lines: 1-2 | anchor: normalize_name | claim: normalize_name owns absent-name normalization
F-2: kind: source | path: src/names.py | lines: 1-2 | anchor: value | claim: the parameter stream anchors the change

## Implementation
CH-1: path: src/names.py | anchor: normalize_name | status: existing | evidence: F-2 | depends_on: none | change: return the empty string for absent names before stripping present names | locality: local | reversibility: reversible | propagation: local

## Verification
T-1: covers: SC-1, CH-1 | given: absent and present input names | when: the targeted names tests execute | then: absent input is empty and present input is stripped | command: python -m pytest tests/test_names.py -q
