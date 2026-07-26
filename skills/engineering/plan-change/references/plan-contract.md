# Plan contract v5

`plan-contract.json` and the generated `plan_runtime.py` are authoritative.
Only one v5 marker and metadata object are allowed. Facts are typed, fingerprinted
repository evidence. The finalizer creates targeted bindings for evidence and
existing change targets; unrelated changes are permitted when those bindings remain
current. The receipt binds the exact plan body and binding JSON.

Use `prepare_plan.py` to create the baseline, inventory, and draft in isolated
storage. `check_plan.py` and `finalize_plan.py` require both the baseline and
inventory. Every inventory candidate must be grounded by an `F-n` and reconciled
through a matching `P-n` disposition or owning `CH-n`; the v5 markdown record
schema itself remains unchanged.
