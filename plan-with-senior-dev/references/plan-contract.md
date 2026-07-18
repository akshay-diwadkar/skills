# Plan Contract v2

The executable source of truth is `plan-contract.json`. Generate a plan with `scripts/scaffold_plan.py`; do not recreate headings or field formats from memory.

## Common skeleton

Every plan starts with an action-oriented H1 followed by `<!-- plan-contract: 2 -->` and the generated tier/task marker. Every tier uses these exact H2 headings in order:

1. Outcome and Scope
2. Evidence Ledger
3. Decisions
4. Implementation Specification
5. Traceability
6. Verification
7. Risks, Assumptions, and Attack

High-Risk plans additionally include `Compatibility and Rollout` and `Durable Rollback`.

## Records

- `SC-n`: one measurable observable success condition.
- `F-n`: one grounded fact using a backticked `path:line`, an anchor present on that exact line, and a precise observation.
- `D-n`: selected approach, cited reason, and nearest rejected alternative with a concrete drawback.
- `CH-n`: backticked path, backticked anchor, `existing` or `new` status, and exact change behavior.
- `T-n`: exact given state/input, exact expected output/error/side effect, and exact command.
- `C-n`: material constraint classified as `preserved`, `modified`, or `at-risk`.
- `R-n P0/P1/P2`: concrete scenario and consequence plus a `Resolution` owned by `CH-n` and `T-n` for every P0/P1.
- `A1`–`A6`: attack result classified as `repaired`, `dismissed`, or `not-applicable`, always with evidence.

Define each ID once. References may repeat. Every `SC-n` and `C-n` needs a Traceability row with `CH-n` and `T-n`; every `CH-n` and `T-n` must appear in Traceability.

## Grounding rules

The checker resolves paths against `--repo-root`, or the current directory when the flag is omitted. Existing `CH-n` anchors must exist somewhere in the target file. New anchors must use `status: new`. A citation whose path, line, or anchor is wrong fails validation.

The checker cannot prove arbitrary natural-language observations. The author must re-read every cited line and ensure the observation follows from the source and surrounding call path.

## Tier requirements

- Tiny requires `SC`, `F`, `D`, `CH`, and `T`, plus attacks A1, A2, and A6.
- Standard additionally requires `C` and all A1–A6 records.
- High-Risk additionally requires `R`, Compatibility and Rollout, and Durable Rollback.

The line maximum is advisory only. Completeness outranks brevity, but remove duplication that does not strengthen evidence, decisions, or verification.
