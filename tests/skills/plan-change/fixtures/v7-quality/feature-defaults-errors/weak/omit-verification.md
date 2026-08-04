# Add default shipping selection

<!-- plan-contract: 7 -->
<!-- plan-metadata: {"intent":"feature","tier":"standard","risk_domains":[]} -->

## Outcome
SC-1: given: missing or invalid shipping input | when: place_order resolves the shipping mode | then: missing input falls back to standard and invalid input is rejected | unchanged: explicit standard and express choices keep working

## Obligations
RQ-1: source: request | anchor: Add default shipping selection | obligation: missing shipping input must fall back to standard shipping | covered_by: SC-1, CH-1

## Evidence
F-1: kind: source | path: src/order.py | lines: 1-4 | anchor: place_order | claim: place_order owns shipping mode resolution

## Implementation
CH-1: path: src/order.py | anchor: place_order | status: existing | evidence: F-1 | depends_on: none | change: treat missing shipping as the standard default and reject invalid shipping before any ordering work | locality: local | reversibility: reversible | propagation: local

## Verification
T-1: covers: SC-1, CH-1 | given: missing, invalid, and explicit shipping inputs | when: the targeted order tests execute | then: the suite executes and reports a passing result | command: python -m pytest tests/test_order.py -q
