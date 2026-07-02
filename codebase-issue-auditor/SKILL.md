---
name: codebase-issue-auditor
description: Audit a repository for evidence-backed bugs, risks, test gaps, architectural friction, performance hotspots, maintainability issues, and developer-experience optimizations, then draft GitHub issues for approval. Use when the user asks Codex to inspect a codebase, identify problems or criticalities, prioritize optimization work, or raise GitHub issues from audit findings.
---

# Codebase Issue Auditor

Audit a local codebase and turn concrete findings into GitHub issue drafts. Publish only after the user approves the draft list.

## Workflow

1. **Establish repo context**
   - Audit the current local working directory by default, or the local path the user explicitly provides.
   - Inspect local `git remote -v`, issue-tracker guidance in `AGENTS.md` or `CLAUDE.md`, `docs/agents/`, `CONTEXT.md`, ADRs, CI config, dependency manifests, test config, and existing issue labels where available.
   - Do not clone or inspect the GitHub issue destination as audit evidence. GitHub is only the publishing target.
   - If repo issue-tracker conventions are missing and the user wants durable setup, use `setup-matt-pocock-skills` first.
   - If `graphify-out/graph.json` exists, use `graphify` queries to orient around architecture and cross-module relationships. If not, use normal repo exploration unless the user asks for a graph.

2. **Audit for evidence-backed findings**
   - Read `references/audit-rubric.md` before drafting findings.
   - Inspect source, tests, dependencies, build scripts, CI, and docs for concrete evidence.
   - Use adjacent skills when they fit the finding type:
     - `diagnose` for suspected bugs or failing behavior.
     - `improve-codebase-architecture` for architectural friction.
     - `to-issues` for converting an approved plan into vertical slices.
     - `triage` for applying the repo's issue-state vocabulary.
   - Do not raise speculative ideas. Every finding needs source locations, command output, dependency metadata, test evidence, or a clear reasoning chain from the implementation.

3. **Draft one issue per root cause**
   - Merge duplicate symptoms into a single root-cause issue.
   - Prefer independently fixable issues over large area-based epics.
   - Default threshold: draft only medium, high, or critical severity findings with high confidence.
   - Include title, body, labels, severity, category, evidence, and acceptance criteria.

4. **Review before publishing**
   - Present the draft issue list with severity, category, confidence, and evidence summary.
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
