---
name: plan-with-senior-dev
description: Turn a requested change — feature, bug fix, refactor, migration, public contract, or risky integration — into a decision-complete implementation plan that another engineer can execute without inventing behavior. Use when the user asks to plan, spec, or think through a code change before writing it. Planning-only; produces no code.
---

# Plan With Senior Dev

Produce an executable specification, not a plausible outline. Remain planning-only: inspect files and run non-mutating checks, but do not edit implementation files. If implementation is later requested, use `implement-with-senior-dev`.

## Non-Negotiables

- Ground every current-state claim in an `F-n` record whose citation, line, and anchor exist.
- Resolve every material product, public-interface, migration, security, and failure-behavior decision before finalizing.
- Reconcile every plan-changing gap between the request and repository evidence, then obtain explicit confirmation of the resolved intent before finalizing.
- Prefer the smallest solution supported by local precedent and constraints.
- Preserve existing parameter, return, wire, error, and side-effect contracts unless an `SC-n` explicitly requires changing them; never widen an interface merely to simplify a local fix.
- Name exact files, symbols, interfaces, branches, errors, side effects, callers, and tests.
- Map every `SC-n` and `C-n` to implementing `CH-n` and verifying `T-n` records.
- Record attacks as repaired, dismissed with evidence, or not applicable. Never manufacture findings.
- Run the checker and repair the plan until it passes; a pass is necessary, not sufficient.

Never guess a repo fact, leave a decision to implementation, ask for a discoverable fact, or end by asking permission to proceed. Alignment confirmation confirms the planning specification; it is not permission to implement.

## Start

1. Inspect repository guidance, status, manifests, tests, configuration, and the request’s likely entry point.
2. Classify one or more task types: `feature`, `bug-fix`, `refactor`, `public-contract`, `security`, `concurrency`, or `external-integration`.
3. Choose the smallest valid tier:
   - `tiny`: one local reversible behavior; no shared contract, durable state, security, concurrency, or external effect.
   - `standard`: multi-file/layer work, internal interfaces, unclear-cause bugs, or meaningful propagation.
   - `high-risk`: public contracts, persisted data, migrations, auth/security, concurrency, payments, or irreversible/external effects.
4. Read only the matching section(s) of [task-playbooks.md](references/task-playbooks.md) and the matching tier section of [worked-examples.md](references/worked-examples.md).
5. Generate the working skeleton:
   `python scripts/scaffold_plan.py --tier <tier> --task-type <type>`.
   The generated headings and field grammar are authoritative; replace every placeholder.

## Checkpoint 1: Frame

Define the observable outcome, audience, measurable `SC-n` records, in-scope surfaces, and explicit invariants. State what must not change. Do not choose an implementation before success and scope are stable.

## Checkpoint 2: Ground

Follow [cognitive-protocols.md](references/cognitive-protocols.md):

1. Locate and read the entry point.
2. Trace one real caller → entry → dependency → side effect → output path.
3. Search analogues, every changed-symbol reference, tests/fixtures, config/schema, generated artifacts, and docs.
4. Record each usable fact as:
   `F-n: path:line | anchor | observation`.

Stop only when current behavior, root cause where relevant, change boundary, callers, invariants, side effects, test gaps, and contradictions are grounded.

## Checkpoint 3: Align

Use the request-to-evidence reconciliation procedure in [cognitive-protocols.md](references/cognitive-protocols.md). Compare the framed request with grounded facts and maintain a temporary gap ledger. A gap is blocking when resolving it could change the outcome, scope, user-visible behavior, shared interface, risk, rollout, or acceptance criteria. Do not interrupt for low-impact reversible details or facts further exploration can discover.

Grill the user on every blocking gap, asking at most three related questions per round. Each question must be scoped to the conflicting or missing intent, cite the relevant request statement and repository evidence, explain the planning consequence, and present two to four mutually exclusive options when feasible. Mark the recommended option and explain why it best fits repository precedent and constraints. Use a scoped free-text question only when the answer space cannot be bounded honestly.

Incorporate each answer into the request baseline and ledger. Re-explore any changed boundary, identify newly exposed gaps, and repeat without a lifetime question limit. When no blocking gap remains, recap the resolved goal, success criteria, audience, in-scope and out-of-scope behavior, invariants, public/shared contracts, constraints, and key decisions. Require explicit user confirmation. If the user corrects the recap, update the baseline and restart alignment; do not draft or finalize the plan until the recap is confirmed.

Fold confirmed outcomes into `SC-n`, `D-n`, and `C-n` records. Keep the gap ledger as working state; do not add it to the final plan.

## Checkpoint 4: Decide

Compare the smallest correct approach with the nearest valid alternative. Record `D-n` with the selected approach, cited reason, and specific rejected drawback.

If implementation comparison exposes another plan-changing request gap, return to Checkpoint 3. Otherwise resolve internal implementation choices from evidence and record them without asking the user.

## Checkpoint 5: Specify

For every change, write a canonical `CH-n` record naming its path, anchor, `existing` or `new` status, exact logic, branches, errors, ordering, and side effects. Show complete before/after shapes for changed public/shared interfaces. Classify each material constraint as `C-n: preserved`, `modified`, or `at-risk`.

Before accepting a signature or schema change, point to the exact success criterion that requires it. If none does, preserve the existing contract and solve inside it.

Order changes by dependency: contracts/data → core logic → orchestration/callers → tests/fixtures → docs/release operations.

## Checkpoint 6: Trace and Verify

Map every `SC-n` and `C-n` to `CH-n` and `T-n`. Every `T-n` must specify exact setup/input, exact output/error/side effect, and an exact command with expected result. Account for every existing changed symbol’s callers, re-exports, fixtures, config/schema, generated surfaces, and documentation.

For High-Risk work, specify mixed-version behavior, rollout order, observability, stop conditions, and durable rollback across code, data, queues, caches, and irreversible effects.

## Checkpoint 7: Attack, Repair, Validate

Read [adversarial-verification.md](references/adversarial-verification.md). Run the contract-required attack records (`A1`–`A6`) and repair every material finding in its owning `CH-n`/`T-n`; do not merely list risk.

Validate from the repository root:

```bash
python scripts/check_plan.py --tier <tier> --repo-root <repo> -
```

Re-read every citation, signature, unchanged claim, trace row, and expected result after the final repair. Finalize only when the checker passes, no unresolved P0/P1 remains, and two literal implementers would make the same material decisions.

## Contract Source

`references/plan-contract.json` is the executable source of truth. Read [plan-contract.md](references/plan-contract.md) only when authoring or debugging the plan format. Do not reproduce its rules elsewhere.
