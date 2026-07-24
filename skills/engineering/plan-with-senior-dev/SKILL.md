---
name: plan-with-senior-dev
description: Turn a feature, bug fix, refactor, migration, public contract, or risky integration into a repository-grounded, decision-complete implementation blueprint. Use when the user wants to plan or spec a code change before implementation. Planning-only; every submitted plan is contract-v3 validated and receipt-stamped.
metadata:
  plan-contract: "3"
  finalizer: "scripts/finalize_plan.py"
  validation-required: "true"
---

# Plan With Senior Dev

Produce an executable blueprint: a literal implementer should be able to follow its records and visual aids without inventing behavior. Remain planning-only. Inspect files and run non-mutating checks, but do not edit implementation files.

## 1. Frame

Classify the applicable task types (`feature`, `bug-fix`, `refactor`, `public-contract`, `security`, `concurrency`, `external-integration`) and choose the smallest valid tier:

- `tiny`: one local reversible behavior; no shared contract, durable state, security, concurrency, or external effect.
- `standard`: multi-file or multi-layer work, an internal interface, an unclear-cause bug, or meaningful propagation.
- `high-risk`: public contracts, persisted data, migrations, authorization, concurrency, payments, or irreversible/external effects.

Read only the matching sections of [task-playbooks.md](references/task-playbooks.md). Define the observable outcome, audience, measurable success criteria, in-scope surfaces, and invariants before selecting an implementation.

Complete this step only when success and scope have one material interpretation.

## 2. Ground

Follow the evidence procedure in [cognitive-protocols.md](references/cognitive-protocols.md):

1. Read the entry point and trace one real caller → entry → dependency → side effect → observable result.
2. Search every changed-symbol reference, re-export, fixture/mock, config/schema, generated surface, documentation contract, and nearest analogue.
3. For bugs, follow evidence-backed causes to the deepest supported root cause.
4. Record only plan-relevant facts as `F-n: path:line | anchor | observation`.

Complete this step only when current behavior, change boundary, callers, invariants, failure paths, side effects, test gaps, and contradictions are grounded. Never ask the user for a discoverable fact.

## 3. Reconcile

Compare the request with repository evidence. Resolve low-impact implementation choices from precedent. Ask the user only when an unresolved choice changes user-visible behavior, a public/shared contract, durable state, security, rollout, or failure semantics and repository evidence cannot decide it.

When asking, state the evidence, planning consequence, mutually exclusive options, and recommendation. Confirmation is required only for such material ambiguity; do not add a blanket recap gate.

Select the smallest correct approach and record the nearest rejected alternative with its specific drawback. Preserve existing parameters, returns, wire shapes, errors, and side effects unless a success criterion requires change.

Complete this step only when no material product or contract decision remains deferred.

## Skill Directory Resolution

Execute bundled runtime commands with the active skill directory (the directory containing this `SKILL.md`) set as the process working directory:
- On Claude Code: set `cwd` to `"${CLAUDE_SKILL_DIR}"` (or the active skill directory) if running from an external working directory.
- On other platforms: execute commands with process `cwd` set to the active skill directory.
- Resolve `skill-root` as the directory containing `SKILL.md` and `repo-root` as the absolute target repository path.
- All non-script paths (target repository, plan, output, draft, payload, `.env`, issue JSON, run-dir) passed as arguments MUST be absolute paths.
- Fail closed if `skill-root` or `repo-root` cannot be resolved.
- Never write output or state files relative to the installed skill package directory.

## 4. Blueprint

Read the matching tier example in [worked-examples.md](references/worked-examples.md), then generate the working scaffold from the active skill directory:

```bash
python scripts/scaffold_plan.py --tier <tier> --task-type <type>
```

Fill the v3 ledger in dependency order: contracts/data → core logic → orchestration/callers → tests/fixtures → generated/docs/operations. Every `CH-n` names its exact path, anchor, behavior, branches, errors, ordering, and side effects. Every `T-n` names exact setup/input, observable expectation, and command. Map every `SC-n` and `C-n` through `CH-n` to `T-n`.

Standard and High-Risk plans require at least one execution blueprint:

`### Execution Blueprint: CH-1, CH-2 — concise purpose`

Choose the smallest aid that makes the hardest part literal:

- typed pseudocode for branching, validation, errors, or ordering;
- Mermaid for cross-component flow, retries, concurrency, or lifecycle;
- complete before/after shapes and compatibility tables for contracts or schemas;
- a dependency or state table when code-shaped pseudocode would obscure the relationship.

Add more than one aid only when each resolves a distinct ambiguity. Keep canonical records outside fenced blocks. Use complete interface shapes rather than prose deltas.

Complete this step only when every success criterion, material constraint, changed surface, failure branch, and verification case is owned, and two literal implementers would make the same material decisions.

## 5. Finalize

Read [adversarial-verification.md](references/adversarial-verification.md). Attack and repair the draft, then pass it through the finalizer from the active skill directory:

```bash
python scripts/finalize_plan.py --tier <tier> --repo-root /absolute/path/to/repository /absolute/path/to/draft.md
```

The finalizer is the only submission path. If it emits any diagnostic, repair the draft and rerun it. If it cannot run, report the validation block instead of presenting a plan. There is no manual or warning-only fallback.

Submit only the exact successful stdout, including its `plan-validation: 3` receipt. When the host requires `<proposed_plan>` tags, wrap the finalized bytes without changing the plan inside them. Never hand-edit finalized output or end by asking permission to proceed.

Complete this step only when `check_plan.py --require-finalized` accepts the exact submitted plan.

## Contract

`references/plan-contract.json` is authoritative. Read [plan-contract.md](references/plan-contract.md) only when debugging format or receipt behavior. Contract v1/v2 plans are invalid; do not adapt or migrate them in this skill.
