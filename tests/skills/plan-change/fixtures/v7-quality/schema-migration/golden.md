# Migrate names to the durable schema

<!-- plan-contract: 7 -->
<!-- plan-metadata: {"intent":"migration","tier":"high-risk","risk_domains":["migration","durable-state"]} -->

## Outcome
SC-1: given: stored names from the prior schema | when: the migration runs | then: every value is normalized exactly once | unchanged: already-normalized names remain stable

## Obligations
RQ-1: source: request | anchor: Migrate stored names to the durable normalized schema | obligation: stored names must converge to the durable normalized schema exactly once | covered_by: SC-1, CH-1

## Evidence
F-1: kind: source | path: src/names.py | lines: 1-2 | anchor: normalize_name | claim: normalize_name defines the durable value transformation
F-2: kind: schema-shape | path: src/schema.json | lines: 1-1 | anchor: version | claim: the schema file declares the durable shape | fields: version, names

## Implementation
CH-1: path: src/names.py | anchor: normalize_name | status: existing | evidence: F-1 | depends_on: none | change: expose an idempotent transformation for the durable-state migration | locality: shared | reversibility: reversible

## Propagation
P-1: surface: contract | disposition: changed | path: src/names.py | owner: CH-1 | reason: F-1

## Boundaries and Risks
B-1: class: durable schema boundary | evidence: F-1 | flow: stored legacy value -> idempotent normalization -> migrated value
R-1: severity: P1 | owner: CH-1 | tests: T-1 | risk: interrupted migration could leave mixed durable representations

## Verification
T-1: covers: SC-1, CH-1 | given: legacy, migrated, and interrupted-state fixtures | when: migration verification executes twice | then: all values converge exactly once without a second mutation | command: python -m pytest tests/test_names.py -q

## Rollout and Rollback
Deploy in bounded batches with checkpoint counts; stop on divergence and restore the last durable snapshot before retrying.
