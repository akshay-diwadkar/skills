# Safety Model & Execution Controls

This repository enforces strict safety standards across all engineering agents and skills to protect codebases, prevent silent failures, and ensure explicit user authorization.

---

## 1. Guarantees & Enforcement Layers

| Safety Guarantee | Policy Definition | Enforcement Mechanism |
| --- | --- | --- |
| **Evidence-First Analysis** | Recommendations must be backed by empirical repository findings, stack traces, or benchmark logs. | Prompt constraints, schema validation scripts. |
| **No Implicit Code Mutations** | Planning, auditing, design, and optimization skills are strictly read-only regarding repository source code. | Read-only access flags (`access.repository_write: false`) and catalog checks. |
| **Explicit Authorization** | Code modifications, file creations, and external writes require explicit user approval. | Permission metadata, platform adapter tool scoping. |
| **Worktree Preservation** | Uncommitted user changes must not be overwritten, stashed without notice, or dirty-reset. | Dirty sentinel checks in `implement-with-senior-dev` scaffolders. |
| **Untrusted Input Protection** | GitHub issue descriptions, external URL content, and user prompt inputs are treated as untrusted claims. | Local checkout reconciliation rules in `github-issue-planner`. |
| **Verifiable Completion** | Claims of success are forbidden unless automated verification commands pass. | Execution contracts in `implement-with-senior-dev` and runner assertions. |

---

## 2. Access Control & Safety Enforcement Model

Agents declare fine-grained access requirements in `catalog/agents.yaml`:

- **Repository Write (`repository_write`)**: Allows modifying workspace source files. Granted only to `delivery-engineer` and `issue-resolution-engineer`.
- **Artifact Write (`artifact_write`)**: Allows writing Markdown plans, evaluation logs, or HTML diagrams to designated artifact outputs.
- **External Write (`external_write`)**: Allows creating or updating remote resources (e.g. GitHub issues). Default is `false` across all agents; explicit user confirmation is required before submitting external writes.

### Host-Enforced vs. Tool-Scoped & Prompt-Enforced Controls

Safety enforcement varies by host platform capabilities:

1. **Host-Enforced Restrictions (Cursor & Codex)**:
   - **Cursor**: Enforces read-only behavior at the host level when `readonly: true` is set in agent frontmatter (`agents/cursor/*.md`).
   - **Codex / OpenAI**: Enforces read-only behavior at the OS/container sandbox level when `sandbox_mode = "read-only"` is set in agent definitions (`.codex/agents/*.toml`).

2. **Tool-Scoped & Prompt-Enforced Restrictions (Claude Code)**:
   - **Claude Code**: Read-only agents omit `Edit` and `Write` tools from their manifest tool declarations (`agents/claude/*.md`).
   - Note: Read-only Claude agents retain `Bash` to run non-mutating inspection commands (such as `pytest`, `git status`, or linter runs). Because `Bash` allows shell commands, read-only guarantees on Claude Code are tool-scoped and prompt-enforced rather than an absolute host sandbox.

---

## 3. Policy Promises vs. Mechanically Enforced Checks

### Mechanically Enforced Checks
1. **Catalog & Manifest Sync**: `sync_catalog.py --check` ensures generated platform adapters match catalog access policies.
2. **Schema & Packaging Integrity**: `validate_repository.py` verifies pinned JSON schemas for Claude and Cursor manifests, exact skill discovery, and ensures distributable packages contain zero test fixtures or dev scripts.
3. **Link Integrity**: `validate_links.py` verifies all relative documentation links.
4. **Execution Contracts**: `scaffold_implementation.py` and `finalize_implementation.py` enforce snapshot hashing and plan contract compliance.

### Policy Rules (Prompt & Agent Instructions)
1. **Root Cause Diagnosis**: Agents must read un-truncated error logs before diagnosing runtime failures.
2. **No Superficial Symptom Patches**: Fixing errors by disabling tests, suppressing exceptions, or returning dummy fallbacks is explicitly prohibited.
3. **Signature Preservation**: Changes to function signatures require updating all invocation sites across the repository.
