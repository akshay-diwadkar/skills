# Plan contract v5

`plan-contract.json` is the sole editable contract source. Generated
`plan_contract_data.py` modules carry that data into standalone skills;
`plan_runtime.py` implements validation behavior against generated data.
Repository validation fails when generated data or synchronized runtimes diverge.
Only one v5 marker and metadata object are allowed. Facts are typed, fingerprinted
repository evidence. The finalizer creates targeted bindings for evidence and
existing change targets; unrelated changes are permitted when those bindings remain
current. The receipt binds the exact plan body and binding JSON.

Both classification passes record `tier_signals`. Any transitive consumer, shared
internal interface, uncertain root cause, multiple architectural layers,
sync-plus-async consumers, or multiple test surfaces requires at least `standard`.
`tiny` requires one existing `local-production`, `reversible` change.

Every final domain retains a complete obligation matrix. A satisfied obligation owns
decision, change, and concept-specific test references. A `not-applicable` obligation
instead owns a concrete `reason` and `F-n` evidence proving absence; contradictory
facts, changes, blueprints, tests, or domain claims fail validation.

Use `prepare_plan.py` to create the baseline, inventory, and draft in isolated
storage. `check_plan.py` and `finalize_plan.py` require both the baseline and
inventory. Every inventory candidate must be grounded by an `F-n` and reconciled
through a matching `P-n` disposition or owning `CH-n`; the v5 markdown record
schema is intentionally breaking within the v5 release wave; regenerate older v5
plans rather than translating them.
