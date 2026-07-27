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

## TypeScript tiny bug fix

The `typescript-tiny` fixture accepts an optional name but calls `trim`
unconditionally. Its complete executable plan is hydrated by
`test_scaffolds_end_to_end.py`; the key structurally verified fact is:

```markdown
- F-1: kind: call-edge | path: src/names.ts | lines: 1-3 | anchor: normalizeName | excerpt-sha256: 4b8db8bdb0e4f14ce60483811f3cf4699ea5c4669770647c8bb8fc56b67fd5db | file-sha256: 4b8db8bdb0e4f14ce60483811f3cf4699ea5c4669770647c8bb8fc56b67fd5db | observation: optional input reaches an unconditional string normalization call | caller: normalizeName | callee: name.trim
```

The tiny plan owns one local null/undefined guard, preserves trim-then-lowercase
ordering, reconciles the direct-caller inventory entry, validates the draft,
finalizes it, and validates the receipt.

## TypeScript standard re-export propagation

The `typescript-standard` fixture defines `parseValue`, re-exports it through
`src/index.ts`, imports that public surface from `src/cli.ts`, and references it
from a test. Prepare with `--tier standard --intent refactor --anchor
src/parser.ts:parseValue`. Representative current facts are:

```markdown
- F-1: kind: function-signature | path: src/parser.ts | lines: 1-3 | anchor: parseValue | excerpt-sha256: 3dec50b40993b4638afd4be0cd170296c720a1c7d3d02d03a2920c7a6ffcd483 | file-sha256: 3dec50b40993b4638afd4be0cd170296c720a1c7d3d02d03a2920c7a6ffcd483 | observation: parseValue is the shared definition | parameters: raw: string | returns: string | async: false
- F-2: kind: documentation-contract | path: src/index.ts | lines: 1-1 | anchor: parseValue | excerpt-sha256: 1cb7da4c83647f5672a5f49abb3679b5a0c3ead2232305771224d328aceaf611 | file-sha256: 1cb7da4c83647f5672a5f49abb3679b5a0c3ead2232305771224d328aceaf611 | observation: the package entry point re-exports parseValue
- P-2: owner: CH-2 | because: F-2 | surface: re-export | disposition: changed
```

The complete plan also grounds and reconciles the CLI and test candidates,
orders definition before re-export before consumers, and verifies unchanged
trimming behavior.

## Kotlin tiny nullable-input bug fix

The `kotlin-tiny` fixture declares `String?` but dereferences it with `!!`.
Kotlin nullability stays inside the existing `parameters` field; no v5 schema
extension is required.

```markdown
- F-1: kind: call-edge | path: src/Names.kt | lines: 1-3 | anchor: normalizeName | excerpt-sha256: e52f4e44cf79e40aca5a99163a4f82f9b16edd880ac64b19b8476805d08f6367 | file-sha256: e52f4e44cf79e40aca5a99163a4f82f9b16edd880ac64b19b8476805d08f6367 | observation: nullable input reaches an unconditional normalization call | caller: normalizeName | callee: name!!.trim
```

The complete tiny plan adds the null branch before existing normalization and
tests null, empty, and padded mixed-case inputs.

## Kotlin standard facade propagation

Kotlin has no native module re-export. The `kotlin-standard` fixture therefore
uses a public forwarding facade in `src/api/ParserApi.kt`, plus a CLI consumer
and test. Prepare with `--tier standard --intent refactor --anchor
src/internal/Parser.kt:parseValue`.

```markdown
- F-1: kind: function-signature | path: src/internal/Parser.kt | lines: 3-5 | anchor: parseValue | excerpt-sha256: 8e340cd1f88670fe330ce81a55680c40417ccdeebb76b4098356dde9ba5ba375 | file-sha256: cd258db861c9cd5fcebbd6cb4a378757bd26e1ba8d7a2e282bfcdbadd27fcc43 | observation: parseValue is the internal shared definition | parameters: raw: String | returns: String | async: false
- F-2: kind: documentation-contract | path: src/api/ParserApi.kt | lines: 1-5 | anchor: parseValue | excerpt-sha256: 964c91274301df4705b168dc3803e2602e6408746955dad838b81d55d30a2057 | file-sha256: 964c91274301df4705b168dc3803e2602e6408746955dad838b81d55d30a2057 | observation: the public facade forwards parseValue
- P-2: owner: CH-2 | because: F-2 | surface: transitive-consumer | disposition: changed
```

The complete plan grounds every facade, CLI, and fixture candidate, updates
them in dependency order, and preserves the parser result and error behavior.

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
