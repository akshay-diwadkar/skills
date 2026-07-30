# Common stateful skill CLI protocol

This release adds a provider-neutral, standard-library CLI protocol for stateful skills with
stable `doctor`, `start`, `status`, `next`, `validate`, and `finalize` commands, a strict JSON
response envelope, typed exit codes, safe path and state handling, and declarative adapters.

`plan-change` is the first reference adapter. Its existing public scripts remain compatible,
while the common runtime can prepare, validate, and finalize a plan through one lifecycle.
