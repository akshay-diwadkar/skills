# Repair-ready structured diagnostics

This minor release gives every blocking skill gate a shared, deterministic
diagnostic contract. JSON failures now identify the owning skill, phase,
artifact, record, field, and path; explain why the failure matters; provide
local evidence and strictness-preserving repairs; and return a replayable next
command. Existing human diagnostics, exit codes, and validation rules remain
unchanged.

The common CLI accepts only canonical child diagnostics, converts unexpected
legacy or process failures into stable adapter diagnostics, and retains legacy
JSON aliases for existing consumers. Standalone skill installations carry the
same synchronized standard-library runtime.
