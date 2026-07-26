# Reproducible v5 worked examples

Every example uses the complete scaffold emitted by `scripts/prepare_plan.py`.
The executable hydration cases in `tests/skills/plan-change/test_scaffolds_end_to_end.py`
reconstruct the repository, fill every fingerprint and placeholder, validate the
draft, finalize it, and validate the receipt.

## Required command order

1. Run `prepare_plan.py` with a grounded `--anchor PATH[:SYMBOL]`.
2. Fill every scaffold field and preserve provisional classification.
3. Run draft `check_plan.py` without `--require-finalized`.
4. Repair baseline and inventory diagnostics until draft validation passes.
5. Run `finalize_plan.py` and save its exact stdout.
6. Run `check_plan.py --require-finalized` against the finalized output.

`--require-finalized` cannot pass before step 5 because the binding and receipt do
not yet exist.

## Tiny local failure

The fixture at `tests/skills/plan-change/fixtures/tiny/` contains
`normalize_name(name: str | None)`. The pipe in that annotation is also the v5
record field separator, so this example uses a structurally verified
`call-edge` fact rather than writing an invalid `parameters` field.

<!-- tiny-plan:start -->
```markdown
# Handle absent names without changing normalization
<!-- plan-contract: 5 -->
<!-- plan-metadata: {"provisional":{"intent":"bug-fix","risk_domains":[],"tier":"tiny","tier_signals":[]},"final":{"intent":"bug-fix","risk_domains":[],"tier":"tiny","tier_signals":[]}} -->

## Outcome and Scope
- SC-1: given: name is None or a non-null string | when: normalize_name runs | then: None returns an empty string | unchanged: non-null names remain stripped and lowercased

## Evidence Ledger
- F-1: kind: call-edge | path: src/names.py | lines: 1-2 | anchor: normalize_name | excerpt-sha256: b30dd7e221cb9ea99152efd997135f3ee5eeb16868b52b422f68b2eceb7ffd62 | file-sha256: ea37618d0f56f1c3b015271c76e85612106fe17d3fc6cd85f939c6c389432ca1 | observation: normalize_name accepts name as str or None but unconditionally calls name.strip then lower, so None raises AttributeError while non-null strings are stripped and lowercased | caller: normalize_name | callee: name.strip

## Decisions
- D-1: selected: add a local None branch that returns an empty string before existing normalization | evidence: F-1 | rejected: remove None from the accepted parameter type | drawback: treating absence as empty preserves the broad input contract but conflates None with an empty normalized name

## Implementation Specification
- CH-1: path: src/names.py | anchor: normalize_name | status: existing | locality: local-production | reversibility: reversible | evidence: F-1 | change: check whether name is None before calling string methods; return an empty string for None, otherwise preserve the existing strip then lower branch ordering with no side effects or caller changes

## Propagation Record
- P-1: owner: CH-1 | because: F-1 | surface: direct-caller | disposition: changed

## Boundary Traces
- B-1: class: Python function input boundary | path: F-1 | flow: caller passes None or str -> normalize_name selects the None or string branch -> caller receives str

## Domain Obligations

## Traceability
| Criterion / constraint | Changes | Tests |
|---|---|---|
| SC-1 | CH-1 | T-1 |

## Verification
- T-1: given: None, whitespace-padded mixed-case text, and an empty string | when: normalize_name is called for each input | then: results are empty string, stripped lowercase text, and empty string respectively, with the None branch running before strip and no side effects | command: python -m pytest tests/test_names.py -q

## Risks, Assumptions, and Attack
- A-forgotten-propagation: status: repaired | finding: the propagation sweep could miss callers relying on normalize_name raising for None | evidence: F-1 | resolution: CH-1 preserves the typed interface and T-1 verifies the consumer-visible result
- A-boundary-input: status: repaired | finding: the None boundary input currently reaches strip and raises AttributeError | evidence: F-1 | resolution: CH-1 adds the explicit None branch and T-1 verifies None, empty, and nonblank inputs
- A-literal-implementation: status: repaired | finding: a literal implementation could reorder lower and strip or introduce a side effect while adding the branch | evidence: F-1 | resolution: CH-1 fixes branch ordering and no-side-effect behavior and T-1 verifies both
```
<!-- tiny-plan:end -->

The exact extraction and `check_plan.py` rerun, with its passing output, are
kept in `validation-evidence.md`. The focused documentation test performs the
same extraction and validation on every test run.

## Standard propagation

Prepare a parser rename with `--tier standard --anchor
src/parser.py:parse_value`. Ground the definition, re-export, CLI importer, and
related test. Give each relevant candidate a `P` disposition, own every changed
path with a `CH`, and use a `domains: none` interface blueprint.

## Security

Prepare with `--tier high-risk --risk-domain security --anchor
src/auth.py:read_record`. The complete scaffold contains every security
obligation, one obligation-specific test per row, and a blueprint covering
principal identity, authorization ownership, and denial behavior.

## Concurrency

Prepare with `--tier high-risk --risk-domain concurrency --anchor
src/billing.py:capture`. Specify shared state and lock/transaction ownership,
the worst interleaving, duplicate retry identity, cancellation, and
reconciliation.

## Migration

Prepare with both `--risk-domain durable-state` and `--risk-domain migration`.
Use separate domain-tagged state blueprints when their owning changes differ, or
one blueprint tagged with both domains when it covers current/target state,
partial and interrupted migration, rollback/roll-forward, verification, and
deployment order.

## New-path ownership

For `src/package/new_module.py`, ground `src/package/__init__.py` with a
`directory-ownership` fact whose `directory` is `src/package`, then cite it as
`directory-owner`. For generated output, cite a `generated-from` fact on the
generator source with exact `generator` and `output`; never cite the output as
its own owner.

## Fail-closed repair

An absent anchor, stale digest, copied obligation ownership, incomplete blueprint
concept group, unrelated new-path owner, baseline mutation, or stale categorized
binding leaves the plan unfinalized. Repair the evidence or plan; never edit the
receipt, remove the diagnostic, or downgrade the tier.
