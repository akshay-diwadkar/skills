# Intent-aware routing and hardened handoff writes

`route-work` 3.2.0 detects execution intent instead of matching execution words: `execution_requested` requires an imperative at the request start, a polite imperative ("please fix", "can you implement"), or an explicitly staged action ("then implement", "and apply"), so "Plan a fix." and "Draft a refactor plan." route to `plan-change` only while "Fix the bug." and "Please update the resolver." add `implement-plan` follow-up.

Handoff persistence is hardened: `handoff_output`, `--output-file`, and `--output-dir` are validated against canonical resolved paths and rejected before any write when they resolve inside the target repository or the installed skill, including through symlinked parents. SKILL.md documents the common-CLI protocol inputs (`handoff_detail`, `handoff_output`) and lists the `route_work.py` direct-script options separately; the `approved_plan` and `issue_number` protocol inputs expose caller-known facts that affect routing.

# Truthful route handoff and corrected routing precedence

`route-work` 3.1.0 returns the `route_handoff` document inline in the decision result; the sealed-file contract is replaced by explicit, truthful wording. The compact routing decision is the default and the detailed step-by-step document is opt-in (`--handoff detailed`); `route-handoff.md` is persisted only through the CLI at a caller-chosen path outside the repository.

Routing precedence is corrected so explicit skill names and chains win, then approved-plan execution, then implicit ideation; noun-only "implementation" no longer triggers execution, and the mermaid route diagram routes audit publication through a `Publish Issues?` decision with complete outgoing branches. The original request text is preserved verbatim in the handoff. Context-load validation now measures the successful stateless run output (including `route_handoff`) for the router.

# Domain-neutral request router skill

Renamed `route-engineering-work` to `route-work` and moved to `skills/routing/route-work`.
The router is now domain agnostic across all repository skills (engineering, research like `ideate`, technical communication like `manualize`).
Each routing decision now emits an ordered `workflow` array of step objects with per-step actionable guidance descriptions.

# Routing marketplace group

A fourth installer group `routing-skills` is now available alongside `engineering-skills`, `research-skills`, and `technical-communication-skills`.
