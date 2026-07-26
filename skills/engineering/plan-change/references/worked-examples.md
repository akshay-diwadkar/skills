# Worked Examples

These are v4 structural excerpts, not plans that can be finalized. Always generate the draft with `scripts/scaffold_plan.py`; it supplies the current contract marker, metadata shape, section order, and placeholders. Replace every angle-bracket placeholder with repository-grounded content. Only `scripts/finalize_plan.py` may write the repository binding and validation receipt.

## Tiny: local null handling

```text
<!-- plan-contract: 4 -->
<!-- plan-metadata: {"provisional":{"intent":"bug-fix","risk_domains":[],"tier":"tiny"},"final":{"intent":"bug-fix","risk_domains":[],"tier":"tiny"}} -->
<!-- plan-repository: {} -->

- SC-1: given: <null input> | when: <function runs> | then: <exact result> | unchanged: <valid-input behavior>
- F-1: path: `<repository-relative path>` | lines: <start>-<end> | anchor: `<anchor>` | excerpt-sha256: `<hash>` | file-sha256: `<hash>` | observation: <current fact>
- D-1: selected: <choice> | evidence: F-1 | rejected: <alternative> | drawback: <concrete drawback>
- CH-1: path: `<repository-relative path>` | anchor: `<anchor>` | status: existing | evidence: F-1 | change: <complete branch behavior>
- P-1: path: `<repository-relative path>` | surface: <consumer or test> | disposition: <changed or grounded no-update> | owner: CH-1.
- B-1: class: <I/O boundary> | path: F-1 | flow: <caller -> behavior -> observable result>.
- T-1: given: <null and valid inputs> | expect: <exact outputs> | command: `<focused command>`.
```

Use this tier only when the classified change has no high-risk domain and no standard signal. The final draft must include every section scaffolded for the tier, including traceability, domain obligations, and required attacks.

## Standard: internal propagation

```text
- CH-1: path: `src/<module>.py` | anchor: `<shared function>` | status: existing | evidence: F-1 | change: <complete internal contract and branch behavior>
- CH-2: path: `tests/test_<module>.py` | anchor: `<regression test>` | status: new | evidence: F-1 | change: <exact propagation regression coverage>

### Execution Blueprint: CH-1 - <behavior flow>
~~~pseudocode
if <new condition>:
    <exact result or error>
else:
    <preserved behavior>
~~~

| Criterion / constraint | Changes | Tests |
|---|---|---|
| SC-1 | CH-1, CH-2 | T-1 |
```

Use a blueprint when the behavior crosses multiple layers or the branch cannot be made unambiguous in a `CH-n` line.

## High-risk: additive event field

```text
- D-1: selected: <additive optional shape and fallback> | evidence: F-1 | rejected: <breaking shape> | drawback: <mixed-version incompatibility>
- CH-1: path: `src/<schema>.py` | anchor: `<event type>` | status: existing | evidence: F-1 | change: <complete old and new shape>
- CH-2: path: `src/<producer>.py` | anchor: `<builder>` | status: existing | evidence: F-2 | change: <defaults, validation, and serialization>
- T-1: given: <old writer/new reader and new writer/old reader> | expect: <exact compatibility results> | command: `<compatibility test command>`.
- O-public-contract: current-shape; proposed-shape; defaults-nullability; error-compatibility; old-writer-new-reader; new-writer-old-reader; generated-clients; mixed-version; compatibility-tests.
- A-compatibility: repaired | evidence: T-1.
- A-forgotten-propagation: repaired | evidence: P-1.
- A-boundary-input: repaired | evidence: T-2.
- A-literal-implementation: repaired | evidence: D-1.
```

For every final risk domain, copy its exact obligation and attack names from `plan-contract.json`; do not infer or abbreviate them.
