---
name: codebase-issue-auditor
description: Audit a repository for bugs, security and performance risks, test gaps, and architectural or maintainability friction, and draft GitHub issues from confirmed findings. Use when asked to inspect a codebase for problems, review overall code quality, hunt for unknown risks, or verify whether prior audit findings were resolved.
---

# Codebase Issue Auditor

Audit broadly, promote strictly, and publish only with explicit approval. Default to every audit category and severity `medium+`; honor explicit time boxes and exclusions as reported limitations.

## Skill Directory Resolution

Execute bundled runtime commands with the active skill directory (the directory containing this `SKILL.md`) set as the process working directory:
- On Claude Code: set `cwd` to `"${CLAUDE_SKILL_DIR}"` (or the active skill directory) if running from an external working directory.
- On other platforms: execute commands with process `cwd` set to the active skill directory.
- Resolve `skill-root` as the directory containing `SKILL.md` and `repo-root` as the absolute target repository path.
- All non-script paths (target repository, plan, output, draft, payload, `.env`, issue JSON, run-dir) passed as arguments MUST be absolute paths.
- Fail closed if `skill-root` or `repo-root` cannot be resolved.
- Never write output or state files relative to the installed skill package directory.

## Workflow

1. **Frame from evidence**
   - Inspect the target repository before asking questions. Read repository guidance, manifests, lockfiles, CI/test configuration, deployment surfaces, issue conventions, `git status`, and the audited commit.
   - Resolve repository facts locally. Ask only when an undiscoverable product decision would materially change scope, priority, or publication.
   - Read [references/audit-protocol.md](references/audit-protocol.md) and create a versioned audit bundle following [references/audit-bundle.md](references/audit-bundle.md). Keep working artifacts outside tracked source unless the user requests a saved report.
   - Complete this phase only when the bundle records the target and commit, dirty-worktree state, scope and limitations, repository boundaries, generated/vendor exclusions, baseline commands, subsystems, and externally exposed or destructive workflows.

2. **Reconcile request and evidence**
   - Compare the requested audit with the grounded repository boundary using the reconciliation procedure in [references/audit-protocol.md](references/audit-protocol.md). Keep the gap ledger as temporary working state, not as a new bundle record.
   - Grill the user only on plan-changing gaps affecting categories, severity, priority, exclusions, output, limitations, or publication intent. Ask up to three related questions per round, cite the request and repository evidence, explain the consequence, offer two to four options when feasible, and recommend one with a repository-grounded reason.
   - Incorporate answers and re-inspect changed boundaries until no blocking gap remains. If reconciliation materially changes the audit frame, recap the resolved frame and require explicit confirmation. This confirmation does not approve publication.
   - If a blocking gap remains unanswered, pause with the exact unresolved gap; do not present a completed audit or publish issues.

3. **Map and inspect every risk surface**
   - Inventory the whole repository, then inspect risk-weighted surfaces rather than mechanically reading generated, vendored, or irrelevant files.
   - Run every applicable category pass and the cross-cutting patterns in [references/deep-analysis-patterns.md](references/deep-analysis-patterns.md). Use [references/ecosystem-optimization.md](references/ecosystem-optimization.md) only after local evidence identifies a concrete ecosystem candidate.
   - Record accepted signals and near-misses while investigating; do not draft issues from first impressions.
   - Complete this phase only when every subsystem/category pair has one coverage record and every risk surface is `accepted`, `clean`, `rejected`, or explicitly `deferred` with evidence, validation actions, and linked candidate/reject records where required.

4. **Disconfirm and promote candidates**
   - Apply [references/audit-rubric.md](references/audit-rubric.md). Test alternative explanations, framework guarantees, reachability, generated/test-only boundaries, and duplicate-root-cause hypotheses.
   - Keep broad discovery but strict promotion. Promote only high-confidence, independently fixable findings at or above the configured severity threshold. Keep everything else in the reject ledger.
   - Complete this phase only when every candidate has a decision and every accepted candidate has a root cause, affected workflow and impact, concrete evidence chain, reproduction or justified non-reproduction, counter-evidence checked, verification path, and independently testable acceptance criteria.

5. **Validate and review drafts**
   - Link one structured issue draft to each accepted root cause. Validate the bundle before presenting it:
     ```bash
     python scripts/validate_audit_bundle.py /absolute/path/to/audit-bundle.json
     ```
   - Present accepted issues with severity, category, confidence, evidence, verification, and relevant rejected near-misses. Report deferred surfaces and other coverage limitations even when no issues survive promotion.
   - Ask the user to approve, reject, merge, split, or reprioritize drafts.
   - Complete this phase only when the validator passes and every omission from the issue list is explained by a reject, deferment, or explicit scope limitation.

6. **Publish approved issues**
   - Require explicit publication approval and a GitHub destination. Check `gh` authentication, then dry-run the exact final bodies and labels:
     ```bash
     python scripts/check_github_env.py --env /absolute/path/to/repository/.env --github-repo-url owner/repo
     python scripts/publish_github_issues.py --input /absolute/path/to/audit-bundle.json --github-repo-url owner/repo
     ```
   - Publish only after the dry run is reviewed:
     ```bash
     python scripts/publish_github_issues.py --input /absolute/path/to/audit-bundle.json --github-repo-url owner/repo --publish
     ```
   - Never publish or close issues implicitly. Exact-title duplicate protection remains enabled by default.

## Resolution Follow-up

For a post-fix audit, reframe the current commit, retest each original root cause and adjacent regression surface, and classify it as `resolved`, `still-open`, or `still-failing`. Require current source or command evidence before calling it resolved. Validate and present the local classification before requesting approval for any external issue closure.

## Legacy Publishing

The publisher continues to accept the legacy issue array and `{ "issues": [...] }` object documented in [references/audit-bundle.md](references/audit-bundle.md). Prefer a validated audit bundle because legacy inputs cannot prove audit coverage.
