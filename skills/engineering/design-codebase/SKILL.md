---
name: design-codebase
description: Decide and justify a repository-grounded codebase design, then emit one plan-ready handoff document. Use for boundary, dependency-direction, state-ownership, abstraction, consolidation, or subsystem design decisions that must be settled before plan-change determines implementation scope and verification.
version: 3.0.2
metadata:
  invocation: both
disable-model-invocation: false
user-invocable: true
---

# Design Codebase

## Purpose and authority

Decide what the target design is and why it is the right structural choice.
Inspect the repository without editing implementation files. Produce one
validated `design-handoff.md` for `plan-change`.

Stop at design. Never classify implementation tier, perform a full propagation
sweep, prescribe file-level edits, write test or execution blueprints, order
migrations or rollout, or attack an implementation. Those responsibilities
belong to `plan-change`. Paths are evidence locators, not edit instructions.

## Start

Resolve `skill-root` to this directory and pass absolute repository, draft, and
output paths:

```bash
python /absolute/skill-root/scripts/cli.py --repo-root /absolute/repo \
  --input draft=/absolute/draft.md \
  --input output_dir=/absolute/output --format json run
```

Run each returned `next_command.argv` with its returned `cwd`. Read only the
current `required_reads`, write only `allowed_writes`, and stop on every
`blocking_reason`.

## Next-step loop

1. Follow the seven completion gates in [Design Protocol](references/design-protocol.md).
2. Use [Bounded Delegation Protocol](references/delegation-protocol.md) for optional read-only review; the primary retains authority.
3. Draft the exact eight-section shape in [Handoff Template](references/handoff-template.md).
4. Use [Worked Example](references/worked-examples.md) only when structural-alternative or interface-contract calibration is needed.
5. Run the stateless `run` command once to seal the draft; it validates,
   backfills local evidence hashes, and writes the single handoff atomically.

Keep claims grounded in current evidence. Compare genuinely different
boundaries or ownership models, define caller-visible signatures, defaults,
nullability, and errors, and leave only planner-owned grounding questions. Use
the protocol's shared vocabulary only where it sharpens the decision.

## Completion and recovery

Complete only when phase `complete` returns exactly
`/absolute/output/design-handoff.md`, its typed receipt and evidence verification
pass, and no other
primary artifact exists. Pass that file to
`plan-change` as `request_file`; the planning agent writes the separate v7
draft after native exploration and seals both inputs with the stateless run.
`plan-change` v7 binds `RQ` anchors to `## Chosen Design & Depth Rationale`
(not Alternatives-only prose).

If sealing fails, repair the draft named by the diagnostic and rerun the same
seal command. If repository evidence changed, refresh the affected evidence
before retrying. Never edit a validated draft or hand off an unverified
document.
