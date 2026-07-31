# Bounded subagent delegation

This minor release adds provider-neutral, optional delegation contracts to
`plan-change`, `audit-codebase`, `design-codebase`, and `implement-plan`.
Bounded read-only scouts and reviewers can broaden evidence collection without
receiving decision, editing, artifact, or publication authority.

Every role now has explicit inputs, scope, output schema, token budget, and stop
condition. Deterministic reconciliation handles conflicts, duplicates,
omissions, and malicious evidence, while an equivalent sequential fallback
keeps platforms without subagent support fully supported.
