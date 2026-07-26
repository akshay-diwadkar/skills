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

For `def normalize_name(raw: str) -> str`, prepare with `--tier tiny --intent
bug-fix --anchor src/names.py:normalize_name`. Own the blank-input branch in
`CH-1`, preserve nonblank behavior in `SC-1`, and verify both outcomes in `T-1`.

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
