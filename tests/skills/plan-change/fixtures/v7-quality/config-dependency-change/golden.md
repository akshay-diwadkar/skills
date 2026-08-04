# Update the pinned dependency

<!-- plan-contract: 7 -->
<!-- plan-metadata: {"intent":"operational","tier":"standard","risk_domains":[]} -->

## Outcome
SC-1: given: the pinned requests dependency and the requester usage | when: the dependency moves to the supported release | then: the pin is updated before the requester adapts | unchanged: the fetch timeout and response behavior remain stable

## Obligations
RQ-1: source: request | anchor: Update the pinned dependency | obligation: the pin must move to the supported minor release and the requester must adapt | covered_by: SC-1, CH-1

## Evidence
F-1: kind: config-key | path: pyproject.toml | lines: 2-2 | anchor: requests | claim: pyproject pins the requests release | key: requests | value: "==2.31.0"
F-2: kind: source | path: src/requester.py | lines: 1-3 | anchor: requests | claim: requester imports the pinned dependency

## Implementation
CH-1: path: pyproject.toml | anchor: requests | status: existing | evidence: F-1 | depends_on: none | change: move the requests pin to the supported minor release | locality: local | reversibility: reversible | propagation: local
CH-2: path: src/requester.py | anchor: requests | status: existing | evidence: F-2 | depends_on: CH-1 | change: adapt the requester call to the compatibility behavior of the new release | locality: local | reversibility: reversible | propagation: local

## Verification
T-1: covers: SC-1, CH-1, CH-2 | given: the updated pin and adapted requester | when: the targeted requester tests execute | then: the dependency resolves and the requester behavior stays stable | command: python -m pytest tests/test_requester.py -q
