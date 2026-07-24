# Design Codebase With Senior Dev

Assess whether architectural change is justified and choose the smallest evidence-backed design, with an incremental behavior-preserving migration path.

This skill is **assessment-only**. It inspects the codebase and runs non-mutating checks, but never modifies implementation source files. It produces a validated, receipt-stamped **Codebase Design Assessment (Contract v2)** artifact.

---

## When to Use

- When evaluating major subsystem restructuring, boundary shifts, or state-ownership changes.
- When assessing whether a proposed architectural refactor or design pattern is justified.
- When evaluating structural technical debt and selecting an evidence-backed disposition.
- When autonomously discovering the primary architectural pain point in a codebase (Mode B).

## When NOT to Use

- For implementing changes directly (this skill is strictly assessment-only).
- For generic repository code-smell auditing or linters (use `codebase-issue-auditor`).
- For measured performance, build, or developer-experience optimization (use `optimize-codebase-with-senior-dev`).

---

## Invocation Modes

### Mode A: Targeted Design Assessment
Used when a specific module, subsystem, file set, dependency boundary, technical debt concern, pattern, or migration is supplied. Assesses the target without expanding into an unrelated repository-wide audit.

### Mode B: Autonomous Target Discovery
Used when the user requests architectural improvement without identifying a specific target. Performs a bounded discovery pass to generate up to 5 candidate targets (`T-n` records), ranks them by structural risk and evidence strength, and autonomously selects the highest-ranked candidate if evidence is direct and scope can be bounded. If evidence is weak or product intent is required, produces a discovery-only assessment and hands off to `codebase-issue-auditor`.

---

## Technical-Debt Dispositions (`TD-n`)

| Disposition | Meaning | Required Fields |
|---|---|---|
| `accept` | Repayment cost exceeds expected interest. | Revisit trigger |
| `monitor` | Interest is plausible but not yet evidenced strongly enough. | Revisit trigger |
| `contain` | Eliminating debt is unsafe or unjustified; bound its blast radius. | Revisit trigger |
| `repay` | Bounded structural change removes recurring interest. | Recurrence guard |
| `retire` | Remove obsolete shims, flags, adapters after exit criteria met. | Recurrence guard |

---

## Contract v2 & Validation Finalization

Finalization is mandatory for submission-ready assessments.

### Bundled Scripts:
1. `scaffold_assessment.py`: Generates starter template for level L0-L3:
   ```bash
   python skills/engineering/design-codebase-with-senior-dev/scripts/scaffold_assessment.py --level L1 --mode targeted
   ```
2. `check_assessment.py`: Validates draft assessment against Contract v2 rules:
   ```bash
   python skills/engineering/design-codebase-with-senior-dev/scripts/check_assessment.py --level L1 --repo-root /path/to/repo /path/to/assessment.md
   ```
3. `finalize_assessment.py`: Emits submission-ready assessment stamped with a SHA-256 validation receipt:
   ```bash
   python skills/engineering/design-codebase-with-senior-dev/scripts/finalize_assessment.py --level L1 --repo-root /path/to/repo /path/to/draft.md > /path/to/finalized.md
   ```

### Receipt Format:
```markdown
<!-- design-assessment-contract: 2; level: L1 -->
<!-- assessment-validation: 2; sha256: 7f8a...3e2b -->
```

---

## Workflow Handoffs (`H-n`)

- `finish assessment`: When no structural change is justified (L0) or the request is fully answered.
- `plan-with-senior-dev`: When the target design is approved and ready for file/symbol-level specification.
- `codebase-issue-auditor`: When no single defensible target can be selected, or repository-wide prioritization/debt inventory is required.
- `optimize-codebase-with-senior-dev`: When the primary bottleneck is measured runtime/tooling performance.
- `implement-with-senior-dev`: Only when an approved, decision-complete implementation plan already exists.
