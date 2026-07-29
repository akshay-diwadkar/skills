---
name: design-codebase
description: Decide and justify a repository-grounded codebase design, then emit one plan-ready handoff document. Use for boundary, dependency-direction, state-ownership, abstraction, consolidation, or subsystem design decisions that must be settled before plan-change determines implementation scope and verification.
version: 1.0.0
---

# Design Codebase

Decide **what** the target design is and **why** it is the right structural
choice. Inspect the repository without editing implementation files. Finish
with one validated `handoff.md` that can be passed, largely unedited, to
`plan-change/scripts/prepare_plan.py --request-file`.

## Out of Scope

Read this section before extending the skill.

Stop at a decided, justified design. Never:

- classify work as tiny, standard, high-risk, or any other tier;
- perform a full-repository propagation sweep;
- propose file-level edits, exact code diffs, or change-specification records;
- write test or execution blueprints;
- order migrations, rollout slices, or rollback actions; or
- attack a proposed implementation.

Those responsibilities belong to `plan-change`. Interface names, signatures,
defaults, nullability, and caller-visible errors are design decisions and
remain in scope. Repository paths may appear only as evidence locators, not as
instructions to edit those files.

## Working Rules

- Ground claims in current repository evidence before deciding.
- Prefer the design with the best functionality-to-interface ratio: hide
  volatile or coupled detail while exposing only what callers must control.
- Compare structural alternatives, not parameter variations of one design.
- Treat consolidation as a real alternative when shallow pieces change
  together.
- Resolve design decisions here. Leave only implementation grounding and
  reconciliation questions to the planner.
- Keep working notes internal. The sole primary artifact is `handoff.md`.

## Skill Directory and Output

Resolve `skill-root` as the directory containing this file and `repo-root` as
the absolute target repository path. Use absolute paths for the repository,
draft, and output directory. Never write working state into the installed skill
directory.

Read `references/handoff-template.md` before drafting. Use
`references/worked-examples.md` when calibration is needed.

## Gates

Complete Gates 1-7 in order.

### Gate 1: Frame the Pressure

Restate the problem for a reader with no prior assessment context. Bound the
behavior and ownership under design without expanding into repository-wide
triage. Complete the gate when the pressure and exclusions are supported by
evidence.

### Gate 2: Build the Evidence Ledger

Record only evidence that supports a design claim. Use the ledger syntax in
`references/handoff-template.md`; cite repository locations precisely and
distinguish repository, request, runtime, and external evidence. Complete the
gate when every material design claim can cite a defined `[E-n]` record.
Local evidence may include an exact line-range `sha256`; finalization computes
it when omitted.

### Gate 3: Compare Structural Choices

Describe the current structure, a chosen structure, and at least one genuinely
distinct alternative. Give each design a boundary, owner, and core abstraction.
Reject parameter-only alternatives. Complete the gate only when one alternative
changes the core abstraction and also changes boundary or ownership, and that
alternative cites evidence not cited by the chosen design rationale.

### Gate 4: Choose Design Depth

Select the design whose exposed interface earns the functionality it provides.
Explain what it hides, what it exposes, and why this ratio improves on today.
Evaluate consolidation whenever tightly coupled shallow pieces created the
pressure. Complete the gate when the choice and rejection rationale are cited.

### Gate 5: Define the Caller Contract

Compare today and the proposed public or shared signatures, defaults,
nullability, and caller-visible errors. State whether the error surface will
`shrink`, remain `flat`, or `grow`; justify growth explicitly. Complete the gate
when a caller can understand the proposed contract without an implementation
plan.

### Gate 6: Complete the Handoff

Fill all eight design sections from `references/handoff-template.md`. State
whether the design covers at least two present-day use patterns or is
intentionally narrow, what a third pattern would change, caller documentation
obligations, and any planner-owned questions. Use explicit evidenced
conclusions instead of placeholders, including when consolidation is not
applicable or no planner questions remain.

Check the draft:

```bash
python scripts/check_assessment.py \
  --repo-root /absolute/path/to/repository \
  /absolute/path/to/draft.md
```

Complete the gate only when the checker exits successfully.

### Gate 7: Finalize One Handoff

Finalize into an output directory:

```bash
python scripts/finalize_assessment.py \
  --repo-root /absolute/path/to/repository \
  --output-dir /absolute/path/to/output \
  /absolute/path/to/draft.md
```

The finalizer emits exactly one document, `/absolute/path/to/output/handoff.md`.
It verifies supplied evidence hashes and backfills every missing local hash.
Before handoff, verify the finalized evidence bindings:

```bash
python scripts/check_assessment.py \
  --repo-root /absolute/path/to/repository \
  --verify-evidence \
  /absolute/path/to/output/handoff.md
```

Submit `handoff.md` as the sole primary artifact and direct `plan-change` to
use it as `prepare_plan.py --request-file`.
