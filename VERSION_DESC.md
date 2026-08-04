# Ideate 1.0.0: Production-grade ideation skill

`ideate` 1.0.0 replaces the initial 0.1.1 release with a production-grade ideation workflow. The explicit 6-step agent workflow (frame, source, research, generate, challenge, rank) replaces the previous minimal Start section. The ideation contract adds required fields for baseline/status quo, success measure, decision criteria, material unknowns, mechanism categories, assumptions and dependencies per candidate, structured experiments, ranking rationale, and conditions that would change the ranking. The validator enforces title positioning, heading uniqueness, field non-emptiness, evidence scoping, mechanism distinctness, table structure, workspace write guards (including symlink resolution), and coherent state/status combinations. The invocation policy changes from `user-invoked` to `both`, enabling agent-selected routing. A 12-scenario live-agent evaluation suite covers software, product, academic, hobby, repo-only, external-only, conflicting evidence, unavailability, stale evidence, prompt injection, safety-sensitive, and fuzzy-goal scenarios.

# Standardize Skill YAML Frontmatter

Standardized YAML frontmatters across all `SKILL.md` files in the repository. Standard key order (`name`, `description`, `version`, `metadata`, `disable-model-invocation`, `user-invocable`) and `metadata` field layout (`invocation` listed first) are now strictly enforced via repository validation.

# Agent-first routing validation

`route-work` 4.0.0 is no longer a request classifier: the agent decides whether skills are needed, which skills to select, the primary skill, exclusions, required capabilities, and caller-known facts, and the router only validates that selection against a declarative skill graph. The result is `{valid, workflow, errors, warnings, route_handoff}`; `workflow` is the agent's selection in stable topological order when valid, unchanged otherwise. The router never inspects request text, never chooses, adds, or removes a skill, and never grants execution authority.

Validation is fail-closed with a documented error catalog: unknown or duplicate skills, excluded prerequisites, missing artifacts (satisfied by a producer earlier in the workflow or a fact such as `audit_handoff_available=true`), approval gates that only facts open (`approved_plan_available` for `implement-plan`), incompatible pairs, unmet required capabilities, and ordering cycles. `raise-issue` always warns that publication approval stays with the user. The machine contract moved from `routing-decision.schema.json` to `schemas/route-validation.schema.json`, the `skill-protocol.json` inputs are the agent-decision fields (`selected_skills`, `primary_skill`, `rationale`, `intent`, `excluded_skills`, `required_capabilities`, and the four fact toggles), and the routing policy documents the authority boundary and every error code. Because selection behavior is backward-incompatible (the `request` text input and the `primary_skill`/`prerequisites`/`follow_up`/`reason`/`confidence`/`next_action`/`allowed_actions`/`forbidden_actions` fields are gone), the skill bumps to 4.0.0 and the repository to 7.0.0.

# Truthful route handoff and corrected routing precedence

`route-work` 3.1.0 returns the `route_handoff` document inline in the decision result; the sealed-file contract is replaced by explicit, truthful wording. The compact routing decision is the default and the detailed step-by-step document is opt-in (`--handoff detailed`); `route-handoff.md` is persisted only through the CLI at a caller-chosen path outside the repository.

Routing precedence is corrected so explicit skill names and chains win, then approved-plan execution, then implicit ideation; noun-only "implementation" no longer triggers execution, and the mermaid route diagram routes audit publication through a `Publish Issues?` decision with complete outgoing branches. The original request text is preserved verbatim in the handoff. Context-load validation now measures the successful stateless run output (including `route_handoff`) for the router.

# Domain-neutral request router skill

Renamed `route-engineering-work` to `route-work` and moved to `skills/routing/route-work`.
The router is now domain agnostic across all repository skills (engineering, research like `ideate`, technical communication like `manualize`).
Each routing decision now emits an ordered `workflow` array of step objects with per-step actionable guidance descriptions.

# Routing marketplace group

A fourth installer group `routing-skills` is now available alongside `engineering-skills`, `research-skills`, and `technical-communication-skills`.
