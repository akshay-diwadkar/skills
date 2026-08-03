# Truthful route handoff and corrected routing precedence

`route-work` 3.1.0 returns the `route_handoff` document inline in the decision result; the sealed-file contract is replaced by explicit, truthful wording. The compact routing decision is the default and the detailed step-by-step document is opt-in (`--handoff detailed`); `route-handoff.md` is persisted only through the CLI at a caller-chosen path outside the repository.

Routing precedence is corrected so explicit skill names and chains win, then approved-plan execution, then implicit ideation; noun-only "implementation" no longer triggers execution, and the mermaid route diagram routes audit publication through a `Publish Issues?` decision with complete outgoing branches. The original request text is preserved verbatim in the handoff. Context-load validation now measures the successful stateless run output (including `route_handoff`) for the router.

# Domain-neutral request router skill

Renamed `route-engineering-work` to `route-work` and moved to `skills/routing/route-work`.
The router is now domain agnostic across all repository skills (engineering, research like `ideate`, technical communication like `manualize`).
Each routing decision now emits an ordered `workflow` array of step objects with per-step actionable guidance descriptions.

# Routing marketplace group

A fourth installer group `routing-skills` is now available alongside `engineering-skills`, `research-skills`, and `technical-communication-skills`.
