# Plan examples

Read only when the required plan depth or record shape is unclear.

These examples calibrate reasoning; they are not text to copy unchanged. Replace
request anchors, paths, lines, commands, and evidence with current facts. Keep
each section once and in canonical contract order.

## Tiny bug fix

**Request:** Fix absent names so `normalize_name(None)` returns `''` without
changing strip behavior for present strings.

**Why tiny:** One behavior owner, one target, no shared fan-out, and no declared
risk domain.

```markdown
# Fix absent-name normalization

<!-- plan-contract: 7 -->
<!-- plan-metadata: {"intent":"bug-fix","tier":"tiny","risk_domains":[]} -->

## Obligations
RQ-1: source: request | anchor: Fix absent names | obligation: absent names must return an empty string while present names retain strip behavior | covered_by: SC-1, CH-1, T-1

## Outcome
SC-1: given: absent and present names | when: normalize_name processes them | then: absent input returns an empty string | unchanged: present input remains stripped

## Evidence
F-1: kind: source | path: src/names.py | lines: 1-3 | anchor: normalize_name | claim: normalize_name owns absent-name and strip behavior

## Implementation
CH-1: path: src/names.py | anchor: normalize_name | status: existing | evidence: F-1 | change: return an empty string before applying strip behavior to present names | depends_on: none | locality: local | reversibility: reversible

## Verification
T-1: covers: SC-1, CH-1 | given: absent and present input cases | when: targeted names tests run | then: the absent case fails before the fix and passes after the fix while present-name stripping remains unchanged | command: python -m pytest tests/test_names.py -q
```

**Stop:** The obligation, owner, behavior change, preserved behavior, and
verification are closed. Do not add Decisions, Propagation, risks, or rollout
without evidence that they affect the task.

## Standard shared refactor

**Request:** Refactor `normalize_name` while keeping the package re-export and
existing callers compatible.

**Why standard:** The owner and public re-export change together, and a caller
is a real propagation surface.

```markdown
# Refactor name normalization ownership

<!-- plan-contract: 7 -->
<!-- plan-metadata: {"intent":"refactor","tier":"standard","risk_domains":[]} -->

## Obligations
RQ-1: source: request | anchor: Refactor `normalize_name` | obligation: refactor the normalization owner without changing observable behavior | covered_by: SC-1, CH-1, T-1
RQ-2: source: request | anchor: keeping the package re-export and existing callers compatible | obligation: preserve the package import and current caller contract | covered_by: SC-1, CH-2, T-1

## Outcome
SC-1: given: direct and package-level imports | when: callers normalize absent and present names | then: both imports retain identical results | unchanged: caller arguments and return expectations remain compatible

## Evidence
F-1: kind: source | path: src/names.py | lines: 1-6 | anchor: normalize_name | claim: names.py owns normalization behavior
F-2: kind: source | path: src/__init__.py | lines: 1-2 | anchor: normalize_name | claim: the package exports normalize_name
F-3: kind: source | path: src/caller.py | lines: 1-5 | anchor: normalize_name | claim: the bounded caller uses the existing argument and return contract

## Implementation
CH-1: path: src/names.py | anchor: normalize_name | status: existing | evidence: F-1 | change: refactor the normalization owner while preserving absent and present-name results | depends_on: none | locality: shared | reversibility: reversible
CH-2: path: src/__init__.py | anchor: normalize_name | status: existing | evidence: F-2 | change: retain the package re-export from the refactored behavior owner | depends_on: CH-1 | locality: shared | reversibility: reversible

## Propagation
P-1: surface: caller | disposition: unchanged | path: src/caller.py | owner: CH-1, CH-2 | reason: F-3 bounded caller inspection confirms that the existing import, arguments, and return expectations remain compatible

## Verification
T-1: covers: SC-1, CH-1, CH-2 | given: direct imports, package imports, and current callers | when: targeted normalization tests run | then: all paths retain absent-name and strip behavior | command: python -m pytest tests/test_names.py tests/test_caller.py -q
```

**Stop:** Every shared change has a distinct affected surface or an
evidence-backed no-impact declaration, dependencies are ordered, and every
outcome and change is verified.

A caller that must change requires its own `CH`; a `P` record alone does not
authorize implementation.

## High-risk migration additions

**Request:** Move tenant events to the new schema within a controlled deployment
window.

**Why high-risk:** The change crosses durable-state and external-integration
boundaries. High-risk does not imply that every change is irreversible.

Start with a complete plan containing `RQ`, `SC`, `F`, `CH`, `P`, and `T`
records. A compatible change graph might be:

1. `CH-1`: deploy consumers that can read both schemas;
2. `CH-2`: enable producer dual-write after `CH-1`;
3. `CH-3`: backfill durable state after `CH-2`;
4. switch reads only after verification proves parity.

Use `conditional` reversibility where recovery depends on retaining the old
schema or data.

Add risk-specific records and rollout guidance:

```markdown
## Boundaries and Risks
B-1: class: event schema boundary | evidence: F-1 | flow: old-schema only -> dual-read and dual-write -> new-schema primary
R-1: severity: P0 | owner: CH-1, CH-2 | tests: T-1 | risk: mixed-version consumers reject or misinterpret new-schema events
R-2: severity: P1 | owner: CH-3 | tests: T-2 | risk: backfilled state diverges from the authoritative old-schema data

## Rollout and Rollback
Deploy dual-read consumers before enabling dual-write producers. Backfill only after mixed-version verification passes, then switch reads after parity remains within the declared threshold. If incompatible-event errors exceed the threshold or parity diverges, disable new-schema writes, return reads to the old schema, and retain old data until recovery completes.
```

**Stop:** Dependencies encode deployment order, every shared change has
propagation accounting, every risk has an owner and verification, and rollout
states the order, trigger, and concrete recovery action.
