# Complete common CLI coverage

This release migrates every executable skill to common CLI protocol 1.0 while
preserving all existing direct scripts and safety boundaries. Stateful skills
now expose lifecycle-specific phases, late immutable inputs, progressive
references, and explicit write permissions. `route-engineering-work` adds a
stateless one-shot protocol result without creating run state.

Audit publication and issue follow-up retain their existing preflight,
dry-run, confirmation, duplicate, and freshness gates. Read-only navigation,
design, routing, and manual auditing do not gain repository write authority.
Installed-package smoke tests cover every skill across Linux, macOS, and
Windows on Python 3.11 and 3.12.
