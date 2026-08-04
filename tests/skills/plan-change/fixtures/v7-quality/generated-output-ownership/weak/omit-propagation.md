# Generate the names adapter

<!-- plan-contract: 7 -->
<!-- plan-metadata: {"intent":"feature","tier":"standard","risk_domains":[]} -->

## Outcome
SC-1: given: a clean checkout without the generated adapter | when: the generator executes | then: it writes the declared adapter module | unchanged: handwritten normalization remains authoritative

## Obligations
RQ-1: source: request | anchor: Generate the names adapter | obligation: the generator must own the declared adapter output | covered_by: SC-1, CH-1

## Evidence
F-1: kind: generated-from | path: tools/gen_names.py | lines: 1-8 | anchor: render_adapter | claim: the generator owns the declared adapter output | generator: tools/gen_names.py | output: src/generated_names.py

## Implementation
CH-1: path: src/generated_names.py | anchor: generated names output | status: new | owner: F-1 | depends_on: none | change: generate an adapter module that delegates to the handwritten normalizer | locality: local | reversibility: reversible

## Verification
T-1: covers: SC-1, CH-1 | given: a clean generated output | when: the generator and targeted tests execute | then: regeneration is stable and delegation passes | command: python tools/gen_names.py && python -m pytest tests/test_names.py -q
