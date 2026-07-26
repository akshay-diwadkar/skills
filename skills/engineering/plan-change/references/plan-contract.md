# Plan contract v5

`plan-contract.json` is the sole editable contract source. Generated
`plan_contract_data.py` modules carry that data into standalone skills;
`plan_runtime.py` implements validation behavior against generated data.
Repository validation fails when generated data or synchronized runtimes diverge.
Only one v5 marker and metadata object are allowed. Facts are typed, fingerprinted
repository evidence. The finalizer creates targeted bindings for evidence and
existing change targets; unrelated changes are permitted when those bindings remain
current. The receipt binds the exact plan body and binding JSON.

Use `prepare_plan.py` to create the baseline, inventory, and draft in isolated
storage. `check_plan.py` and `finalize_plan.py` require both the baseline and
inventory. Every inventory candidate must be grounded by an `F-n` and reconciled
through a matching `P-n` disposition or owning `CH-n`; the v5 markdown record
schema is intentionally breaking within the v5 release wave; regenerate older v5
plans rather than translating them.
