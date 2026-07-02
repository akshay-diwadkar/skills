---
name: github-issue-planner
description: Fetch open GitHub issues for a specified repository, read issue bodies and comments, inspect the local codebase, and write decision-complete implementation plans to a local Markdown report. Use when the user asks to fetch open issues, plan issue fixes, prepare a GitHub issue backlog for implementation, or produce local plans for resolving GitHub issues without writing back to GitHub.
---

# GitHub Issue Planner

Fetch open non-PR GitHub issues, use the local codebase as the implementation source of truth, and write one resolution plan per issue. GitHub is read-only in this skill.

## Workflow

1. **Resolve inputs**
   - Ask for `--github-repo-url` if the user did not provide a GitHub repository URL or `owner/repo`.
   - Use the current local working directory as the codebase by default, or a local path explicitly provided by the user.
   - Do not clone or inspect the GitHub repository as the code source. Use GitHub only for issue metadata.

2. **Check GitHub access**
   - Use `.env` in the current directory or this skill folder, or an explicit `--env` path.
   - Validate token configuration:
     ```bash
     python scripts/check_github_env.py --env .env --github-repo-url https://github.com/owner/repo
     ```

3. **Fetch open issues**
   - Fetch all open non-PR issues and comments:
     ```bash
     python scripts/fetch_github_issues.py --env .env --github-repo-url https://github.com/owner/repo --output .scratch/github-issue-plans/issues.json
     ```
   - Treat the JSON output as the GitHub issue context. Do not write labels, comments, or state changes back to GitHub.

4. **Choose planning engine**
   - If `plan-with-senior-dev` is available, ask the user whether to use it for issue-resolution planning.
   - If the user approves, use `plan-with-senior-dev` for each issue after fetching issue context and exploring local code.
   - If the user declines or `plan-with-senior-dev` is unavailable, read `references/planning-rubric.md` and follow it directly.

5. **Explore local code**
   - For each issue, inspect the local codebase, tests, docs, config, and nearby patterns relevant to the issue.
   - Cite local files and commands in the plan where they support implementation decisions.
   - Mark the issue as `needs-info` in the report when the issue lacks enough detail to plan safely.

6. **Write the report**
   - Write a Markdown report under `.scratch/github-issue-plans/<owner-repo>/<timestamp>.md`.
   - Include one section per issue with issue summary, local findings, decision-complete plan, test strategy, risks, and assumptions.
   - End by summarizing the report path and top priorities in chat.

## Report Shape

Each issue section should include:

- issue number, title, URL, labels, author, and timestamps;
- planning status: `ready-to-plan`, `needs-info`, or `blocked`;
- summary of the issue body and relevant comments;
- local codebase findings with file references;
- implementation plan that leaves no decisions to the implementer;
- verification commands and expected passing result;
- risks and assumptions.

## GitHub Configuration

Create `.env` from `.env.example` or export equivalent variables:

```dotenv
GITHUB_TOKEN=
GITHUB_ISSUE_FETCH_LABELS=
GITHUB_ISSUE_FETCH_LIMIT=
```

Safe env handling:

- `.env.example` is safe to read.
- `.env` is sensitive and must be treated as a secret-bearing file.
- Never directly read `.env` in the agent context: do not run `cat .env`, `Get-Content .env`, `type .env`, `rg ... .env`, `Select-String ... .env`, or equivalent commands.
- Never inspect `.env` contents to debug authentication. If debugging is needed, inspect only existence, size, or path metadata.
- Pass `.env` paths only to trusted bundled scripts via `--env`; checker output must mask tokens.

`GITHUB_TOKEN` is required. Labels and limits are optional defaults only. Pass the repository target per run with `--github-repo-url`. Trusted bundled scripts may parse `.env` internally when passed `--env`; the agent must not read the file directly.

## Safety Rules

- Do not comment on GitHub issues.
- Do not apply or remove labels.
- Do not close issues.
- Do not implement code fixes.
- Do not treat GitHub repository contents as the codebase; only the local checkout is the code source.
