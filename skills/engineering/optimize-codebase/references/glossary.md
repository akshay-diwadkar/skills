# Optimize-Codebase Handoff Glossary

This glossary is the semantic companion to the optimization artifacts. The
machine-valid paths, fields, values, and section shapes remain authoritative in
`optimization-contract.json` and `handoff-contract.json`; candidate promotion
rules remain authoritative in `optimization-rubric.md`. If this glossary
disagrees with either source, correct the glossary rather than reinterpreting
the contract.

## Artifact Coordinates

| Term | Plain-English meaning |
|---|---|
| `fast` path | An already-authorized, single-file, single-symbol implementation run that satisfies every fast-path eligibility key. |
| `full` path | The evidence, comparison, classification, and handoff process used whenever any fast-path condition is unproved. |
| `targeted` scope | Investigation of one named workflow or pain point, traced end to end. |
| `sweep` scope | Explicit repository-wide discovery using an exhaustive subsystem/pass coverage matrix and bounded deep-dives. |
| `plan` stage | A decision-complete recommendation without repository implementation. Authorization remains `plan-only`. |
| `implementation` stage | One explicitly authorized candidate is applied, verified against its baseline, and retained or rolled back from evidence. |
| Workflow | The observable operation whose cost or maintainability is being optimized; it is copied unchanged into a plan-change request. |
| Protected behavior | Output, errors, effects, ordering, compatibility, coverage, or release behavior that the optimization must preserve unless explicitly authorized to change. |

## Record Ownership

`n` is a positive integer. Each record family owns one kind of claim so a
downstream owner can distinguish evidence, decisions, verification, and
execution.

| Form | Ownership |
|---|---|
| `F-n` | Verified repository fact: an existing `path:line`, exact symbol anchor, and observation. |
| `CV-n` | One subsystem/pass coverage disposition, its evidence, priority, and resume action. |
| `B-n` | Baseline for one named workflow, including its method, raw result or blocker, confidence, and `F-n` evidence. |
| `R-n` | Version-matched official capability research tied to a `B-n`, or an explicit not-applicable local-code finding. |
| `C-n` | One independently measurable mechanism with evidence, literal anchors, promotion gates, classification band, verification, and rollback. |
| `V-n` | Exact proof method for one `C-n` and the observable result that would satisfy it. |
| `X-n` | Evidence-backed rejection or deferral plus the condition that permits reconsideration or resumption. |
| `H-n` | The single next-owner decision for the run and the selected candidate that owner receives. |
| `E-n` | The explicitly authorized action and attributable result for one implemented candidate; valid only at implementation stage. |

References flow forward: `F-n` grounds baselines and coverage; `B-n` selects
research; `F-n`/`B-n`/`R-n` support `C-n`; `V-n` proves `C-n`; and `H-n`
transfers the selected candidate. A handoff must preserve those identifiers so
the receiver can trace every copied claim to its owning record.

## Baseline Vocabulary

| Term | Plain-English meaning |
|---|---|
| Measured baseline | A reproducible command result with raw values, units or counts, workload, and conditions suitable for comparison. |
| `bounded-static` baseline | A complete, explicitly delimited observation supporting only a non-runtime claim, such as propagation count, duplicated branches, setup steps, feedback stages, or navigation hops. |
| `blocked` baseline | A named missing access, data set, or environment plus a safe confirmation experiment; it cannot support promotion beyond `investigate`. |
| Comparable baseline | Before and after evidence collected with the same workflow, workload, runtime, cache state, aggregation, and relevant environment. |

## Candidate Outcomes

These terms describe disposition, not implementation authorization. The exact
promotion gates and deterministic ordering live in
`optimization-rubric.md`.

| Contract value | Plain-English meaning |
|---|---|
| `quick-win` (Quick Win) | A high-confidence, low-effort, low-risk, low-blast-radius, strongly verified, independent, and reversible mechanism with every gate satisfied. |
| `strategic-win` (Strategic Win) | A high-impact, independently measurable and reversible mechanism whose coordination, risk, or blast radius requires explicit downstream planning. |
| `investigate` (Investigate) | A credible mechanism blocked only by baseline or compatibility evidence and paired with a safe confirmation experiment; it is not a win. |
| `rejected` (Rejected) | A mechanism that fails promotion or ordering and carries evidence plus a concrete revisit condition. |
| Winning candidate | The `C-n` named by both the recommendation and `H-n`; only this candidate may be transferred or executed. |

## Anchors and Handoff Ownership

### Literal anchor

A literal `path:symbol` anchor combines the repository-relative path from a
cited `F-n` with that fact's exact symbol text. It is not a prose location, line
number, glob, directory, or inferred rename. The winning `C-n`, every `Anchor`
line in `request.md`, and the downstream `--anchor` argument carry identical
bytes.

### Next owner

Every full-path artifact contains exactly one `H-n` with one of these contract
states:

| State | Receiver and required payload |
|---|---|
| `finish optimization` | No downstream implementation-planning artifact is required; the optimization run ends with its evidence, decision, and limitations. |
| `plan-change` | The plan-change skill receives a separate validated `request.md` for a Strategic Win, including the winning evidence and every literal anchor. |
| `implement-plan` | An approved, decision-complete implementation plan already exists and is the execution authority; the optimization report does not replace it. |

### Separate `request.md`

`request.md` is a distinct handoff artifact, never a section embedded in the
optimization report. Its workflow, goal, success criteria, protected behavior,
constraints, exclusions, candidate, band, mechanism, evidence, and anchors are
copied from the validated run. The artifact marker and exact field shape are
defined by `handoff-contract.json`.

### Plan-change invocation

`Tier`, `Intent`, and `Risk domains` are downstream plan-change invocation
coordinates, not optimization ratings. Use only values accepted by
`handoff-contract.json`; use `Risk domains: none` when no `--risk-domain`
argument is passed. Their planning semantics are defined in
`../../plan-change/references/glossary.md`. Do not weaken a tier, omit a
plausible risk domain, or reinterpret an optimization band as a plan tier.
