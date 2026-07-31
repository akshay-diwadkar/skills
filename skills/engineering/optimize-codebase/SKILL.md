---
name: optimize-codebase
description: Run a multi-gate, evidence-backed optimization process for a named performance, build, CI, dependency, maintainability, or developer-experience workflow. Use targeted mode for a known pain and sweep mode only for explicit repository-wide discovery; implementation requires explicit authorization, with a strict Quick-Win fast path for already-authorized single-symbol changes.
version: 2.1.0
---

# Optimize Codebase

Start the common CLI with `request_file`; do not guess path or scope. Review
the deterministic classification in `result`, then run `next` to apply it.
Override only with hash-bound contrary request or current-source evidence.

Select an execution path before producing an artifact. Evidence selects the leverage point; ecosystem documentation only validates an evidence-selected mechanism.

Use `scripts/cli.py` as the primary executable entrypoint. Supply `path`,
`scope`, `stage`, `report`, and `implementation_authorized`; the common
protocol scaffolds the selected artifact and exposes only its relevant
references. Repository writes are available only for an explicitly authorized
implementation stage. Existing scaffold and checker commands remain supported.

## Resolve the Skill

- Set `skill-root` to the directory containing this file and `repo-root` to the absolute target repository.
- Run bundled scripts with `skill-root` as the process working directory.
- Pass absolute paths for repositories, reports, handoffs, run directories, and payloads.
- Never write output relative to the installed skill directory.
- Fail closed when either root is unresolved.

## Select the Path

Use `fast` only when every criterion below is already proved. Otherwise use `full`; do not ask the user to weaken a criterion.

### Fast Path Detection

All criteria are mandatory:

1. The current request explicitly authorizes implementation.
2. Scope is targeted: exactly one existing tracked file and one named existing function or symbol.
3. One independently measurable mechanism completely addresses the request.
4. Protected behavior, compatibility, acceptance threshold, verification, and rollback are unambiguous.
5. Confidence is high; effort, risk, and blast radius are low; the patch is independent and reversible.
6. No public API, schema, persistence, security/auth, concurrency, external effect, deployment/release, generated output, dependency/version, shared configuration, or cross-module propagation can change.
7. The cited file has no overlapping dirty-worktree change.
8. One comparable measurement or complete bounded-static baseline exists, and the exact post-change verification is runnable.

Generate and fill the fast artifact:

```bash
python scripts/scaffold_optimization.py --path fast --scope targeted --stage implementation
python scripts/check_optimization.py --path fast --scope targeted --stage implementation --repo-root /absolute/repo /absolute/report.md
```

The artifact contains exactly one `F-n`, one `B-n`, and one `C-n`. `C-1` must be `quick-win`, affirm every contract eligibility key, cite only F-1/B-1, carry the exact `path:symbol`, and embed the mechanism, threshold, verification, expected result, and rollback. After it validates, apply only that mechanism, run the embedded verification, compare against B-1, and revert the introduced patch if behavior regresses or the result is neutral, worse, or inconclusive.

**Completion criterion:** the authorized patch and verification are attributable to C-1, or the run has routed to `full`.

## Full Path Records

Before constructing any full-path record, read `references/glossary.md`
completely. It defines record ownership, baseline and candidate vocabulary,
literal-anchor identity, and the downstream meaning of every handoff state.

Read `references/optimization-protocol.md` before collecting full-path evidence and `references/optimization-rubric.md` before constructing or classifying candidates. Read ecosystem and pattern references only after a B-n identifies the relevant component or pass.

Generate the artifact before filling it:

```bash
python scripts/scaffold_optimization.py --path full --scope targeted|sweep --stage plan|implementation
```

## Full Path: Eight Gates

Complete the gates in order. If later evidence changes scope, stage, or candidate selection, regenerate the scaffold and repeat every affected gate.

### Gate 1: Frame and Protect

Inspect repository guidance and worktree state. Record scope, stage, authorization, workflow, goal, measurable success criteria, constraints, exclusions, risk tolerance, and protected behavior. Treat implementation as unauthorized unless the user explicitly requested edits.

**Completion criterion:** the target and threshold are observable, authorization is exact, protected behavior is explicit, and every discoverable fact was resolved locally.

### Gate 2: Trace and Cover

For targeted work, trace the named workflow end to end. For a sweep, inventory stable subsystems and applicable passes, create every subsystem/pass CV-n pair, triage breadth before depth, and deep-dive at most three candidate surfaces per wave. Every pair ends as `candidate`, `clean`, `rejected`, or `deferred`; every deferral is prioritized and resumable.

**Completion criterion:** the targeted path is grounded end to end, or the sweep matrix is exhaustive with no silent omissions.

### Gate 3: Baseline

Apply the baseline protocol to the named workflow. Every candidate surface receives a B-n that measures it, supplies complete bounded-static evidence, or records an actionable blocker.

**Completion criterion:** every B-n satisfies the canonical evidence and comparability rules.

### Gate 4: Align

Apply the request-to-baseline alignment protocol. Resolve every gap that could change the workflow, metric, scope, behavior, compatibility, constraints, risk, candidate eligibility, rollback, or authorization. Require explicit confirmation of the resolved brief; this confirmation does not itself authorize implementation.

**Completion criterion:** no blocking gap remains and the resolved brief is explicitly confirmed.

### Gate 5: Research

Research only components selected by B-n evidence. Resolve the actual version, configuration, runtime mode, deployment target, ownership, and usage. Use specific official documentation for the resolved version; local-code candidates use an explicit not-applicable R-n.

**Completion criterion:** every ecosystem claim has local usage evidence, version-matched documentation, compatibility analysis, and a B-n link.

### Gate 6: Compare and Classify

Construct independent candidates and apply every gate and ordering rule in `references/optimization-rubric.md`. Keep serious alternatives and their rejection or deferral evidence.

**Completion criterion:** every candidate has one deterministic band, selected anchors derive from cited F-n records, and the winner beats alternatives under the confirmed constraints.

### Gate 7: Plan or Implement

For plan stage, specify dependency-ordered changes, exact file/symbol areas, behavior guardrails, compatibility, tests, acceptance criteria, rollback, residual risk, and one H-n.

For full implementation stage:

1. Require explicit implementation authorization and E-n.
2. Require a checker-passing plan with an eligible Quick or Strategic Win.
3. Reconfirm the worktree, comparable baseline, regression surface, and rollback.
4. Apply one independently measurable candidate.
5. Run behavior checks and the comparable after-baseline.
6. Stop and revert only the introduced patch when evidence or behavior fails.

**Completion criterion:** the plan is decision-complete without edits, or one authorized candidate has an attributable patch, comparable before/after evidence, and rollback status.

### Gate 8: Validate and Handoff

Run:

```bash
python scripts/check_optimization.py --path full --scope targeted|sweep --stage plan|implementation --repo-root /absolute/repo /absolute/report.md
```

Emit exactly one H-n: `finish optimization`, `plan-change`, or `implement-plan`.

For `plan-change`, produce a separate file beginning with:

```markdown
# Plan-Change Request
<!-- artifact: request.md; handoff-contract: 1 -->
```

Give it exactly the sections and fields in `references/handoff-contract.json`. Copy every literal `path:symbol` from the winning C-n and its cited F-n records. State plan-change `Tier`, `Intent`, `Risk domains`, and one `Anchor` line per anchor. Use `Risk domains: none` when `--risk-domain` must be omitted. Validate both artifacts:

```bash
python scripts/check_optimization.py --path full --scope targeted --stage plan --repo-root /absolute/repo --handoff-file /absolute/request.md /absolute/report.md
```

When no output path is available, emit the request as a distinct filename-marked payload so the caller can materialize its bytes unchanged; never substitute a section inside the optimization report.

**Completion criterion:** the checker passes, every deferral and residual risk is visible, and exactly one next owner receives every required artifact.

## Handoff Boundaries

- Use `audit-codebase` when the problem or defect has not been proved.
- Use `plan-change` for a Strategic Win needing implementation contracts and propagation analysis.
- Use `implement-plan` for an approved decision-complete plan.
- Use `design-codebase` when structural redesign, rather than measurable optimization, is primary.
