---
name: codebase-issue-auditor
description: Audit a repository for evidence-backed bugs, risks, test gaps, architectural friction, performance hotspots, maintainability issues, and developer-experience optimizations, then draft GitHub issues for approval. Use when the user asks Codex to inspect a codebase, identify problems or criticalities, prioritize optimization work, or raise GitHub issues from audit findings.
---

# Codebase Issue Auditor

Audit a local codebase and turn concrete findings into GitHub issue drafts. Optimize for missed-finding reduction: use systematic coverage before drafting, and publish only after the user approves the draft list.

## Workflow

1. **Frame the audit**
   - Audit the current local working directory by default, or the local path the user explicitly provides.
   - Inspect local repo guidance before judging the code: `git remote -v`, `AGENTS.md` or `CLAUDE.md`, `docs/agents/`, `CONTEXT.md`, ADRs, CI config, dependency manifests, test config, and existing issue-label guidance where available.
   - Do not clone or inspect the GitHub issue destination as audit evidence. GitHub is only the publishing target.
   - If repo issue-tracker conventions are missing and the user wants durable setup, use `setup-matt-pocock-skills` first.
   - If `graphify-out/graph.json` exists, use `graphify` queries to orient around architecture and cross-module relationships. If not, use normal repo exploration unless the user asks for a graph.
   - Complete this step only when you can state the repo purpose, primary runtime/tooling, test/CI shape, deploy or package surface if present, and issue-tracker conventions if present.

2. **Run the audit protocol**
   - Read `references/audit-protocol.md` and follow it before drafting issues.
   - Read `references/audit-rubric.md` before accepting or rejecting candidate findings.
   - Build the protocol artifacts in working notes: ecosystem inventory, risk map, coverage matrix, candidate ledger, and reject ledger.
   - Use adjacent skills only when they match a candidate type: `diagnose` for suspected failing behavior, `improve-codebase-architecture` for architectural friction, `to-issues` for converting an approved plan into vertical slices, and `triage` for applying the repo's issue-state vocabulary.
   - If local ecosystem inventory reveals a concrete framework, package, runtime, build tool, test tool, deployment target, or CI/tooling setup that may be misused, read `references/ecosystem-optimization.md` before using web evidence for that candidate. Do not run ecosystem web research without local evidence first.
   - Complete this step only when every high-risk area in the coverage matrix has either an accepted candidate finding or a recorded reject reason.

3. **Draft one issue per root cause**
   - Draft only candidates that pass the default threshold in `references/audit-rubric.md`.
   - Merge duplicate symptoms into a single root-cause issue.
   - Prefer independently fixable issues over large area-based epics.
   - Each draft must include the schema fields below. Put the verification path in the issue body, and report confidence in the review summary rather than adding new JSON fields.
   - Complete this step only when every drafted issue can be pasted into GitHub with enough evidence for a maintainer to reproduce, verify, or confidently plan the fix.

4. **Review before publishing**
   - Present the draft issue list with severity, category, confidence, evidence summary, verification path, and any rejected near-misses worth knowing about.
   - Ask the user to approve, reject, merge, split, or reprioritize drafts.
   - Do not publish until the user explicitly approves publication.

5. **Publish with the bundled script**
   - Save approved drafts as JSON using the schema below.
   - Ask for the GitHub repository URL to publish issues to. Accept `https://github.com/owner/repo`, `git@github.com:owner/repo.git`, or `owner/repo`.
   - Check token configuration before publishing:
     ```bash
     python scripts/check_github_env.py --env .env
     ```
   - Optionally validate the destination:
     ```bash
     python scripts/check_github_env.py --env .env --github-repo-url https://github.com/owner/repo
     ```
   - Run a dry run first:
     ```bash
     python scripts/publish_github_issues.py --input issues.json --env .env --github-repo-url https://github.com/owner/repo
     ```
   - After approval, publish:
     ```bash
     python scripts/publish_github_issues.py --input issues.json --env .env --github-repo-url https://github.com/owner/repo --publish
     ```

6. **Resolution follow-up after fixes**
   - Use this branch when rerun after implementation work.
   - Compare current audit findings against open audit or GitHub issues supplied by the user, fetched through approved issue metadata, or referenced in the implementation plan.
   - Re-run enough of `references/audit-protocol.md` to test the original root cause and its adjacent regression surface.
   - Classify each relevant open issue as `resolved`, `still-open`, or `still-failing`.
   - Mark an issue `resolved` only when source evidence, passing tests, command output, or a clean rerun shows the original finding no longer reproduces.
   - Present resolved issue candidates with issue number or URL, original finding summary, current evidence, verification path, and residual risk.
   - Do not close GitHub issues automatically. Ask for explicit user approval before closing any issue.
   - If GitHub credentials or the repository URL are missing, produce the resolved/open/still-failing classification locally and stop before any external write.

## Issue Draft Schema

The publisher accepts either a JSON array of issues or an object with an `issues` array.

```json
[
  {
    "title": "Short actionable title",
    "body": "GitHub Markdown issue body",
    "labels": ["audit", "needs-triage"],
    "severity": "high",
    "category": "bug",
    "evidence": ["src/example.ts:42 explains the failing path"],
    "acceptance_criteria": ["Regression test covers the failing path"]
  }
]
```

Allowed categories: `bug`, `security`, `performance`, `test-gap`, `architecture`, `maintainability`, `developer-experience`.

Allowed severities: `critical`, `high`, `medium`, `low`.

## GitHub Configuration

Copy `.env.example` to `.env` outside source control and fill in the values:

```dotenv
GITHUB_TOKEN=ghp_xxx
GITHUB_DEFAULT_LABELS=audit,needs-triage
GITHUB_SKIP_DUPLICATES=true
```

Safe env handling:

- `.env.example` is safe to read.
- `.env` is sensitive and must be treated as a secret-bearing file.
- Never directly read `.env` in the agent context: do not run `cat .env`, `Get-Content .env`, `type .env`, `rg ... .env`, `Select-String ... .env`, or equivalent commands.
- Never inspect `.env` contents to debug authentication. If debugging is needed, inspect only existence, size, or path metadata.
- Pass `.env` paths only to trusted bundled scripts via `--env`; checker output must mask tokens.

Check configuration without printing secrets:

```bash
python scripts/check_github_env.py --env .env
```

The trusted publisher script parses `.env` internally when passed `--env`, so loading variables into the shell is optional. The `.env` stores the GitHub token and optional defaults only; it does not hardcode the issue destination. Pass the destination per run with `--github-repo-url`.

If another tool needs the variables in the current shell, use the matching loader:

PowerShell:

```powershell
.\scripts\load_github_env.ps1 -EnvPath .env
```

Bash or zsh:

```bash
source scripts/load_github_env.sh .env
```

When `--env` is provided, the checker and publisher use that file plus already-exported environment variables. Without `--env`, they read `.env` from the current working directory first, then from this skill folder if present. Environment variables already set in the shell take precedence. `GITHUB_REPOSITORY` is ignored by the normal publishing flow; use `--github-repo-url` instead.

## Publishing Guardrails

- Dry-run mode is the default and never calls the GitHub API.
- `--publish` is required for network writes.
- Duplicate protection is enabled by default and skips open issues with the same title.
- Never commit a real `.env` containing secrets. Keep `.env.example` as the only tracked env template in the skill.
