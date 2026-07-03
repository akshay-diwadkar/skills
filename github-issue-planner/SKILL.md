---
name: github-issue-planner
description: Fetch open GitHub issues, use the local checkout as the implementation source of truth, and write decision-complete local Markdown plans. Use when the user asks to plan GitHub issue fixes, prepare an implementation backlog from GitHub issues, inspect open issues before coding, or produce read-only issue-resolution plans without writing back to GitHub.
---

# GitHub Issue Planner

Fetch open non-PR GitHub issues, inspect the local checkout, and write one resolution plan per issue. GitHub is read-only in this skill.

## Workflow

1. **Resolve inputs**
   - Set `$skillDir` to this skill folder and use it for every bundled script path.
   - Use the current working directory as the codebase unless the user provides a local path.
   - Use the user's GitHub URL or `owner/repo` when provided.
   - If no GitHub target is provided, infer `owner/repo` from the local checkout's GitHub remote. Ask only when inference fails or multiple GitHub remotes conflict.
   - Do not clone or inspect GitHub repository files. GitHub provides issue metadata only.

2. **Preflight**
   - Use `.env` in the current directory or this skill folder, or an explicit `--env` path.
   - Validate token and optional config without exposing secrets:
     ```powershell
     $skillDir = 'C:\Users\Akshay Diwadkar\.agents\skills\github-issue-planner'
     python "$skillDir\scripts\check_github_env.py" --env .env --github-repo-url owner/repo
     ```
   - If preflight fails, report the missing or invalid configuration and stop.

3. **Fetch open issues**
   - Fetch all open non-PR issues and comments:
     ```powershell
     $skillDir = 'C:\Users\Akshay Diwadkar\.agents\skills\github-issue-planner'
     python "$skillDir\scripts\fetch_github_issues.py" --env .env --github-repo-url owner/repo --output .scratch/github-issue-plans/issues.json
     ```
   - Treat the JSON output as the only GitHub issue context. Do not write labels, comments, or state changes back to GitHub.

4. **Explore local code**
   - For each issue, inspect the local codebase, tests, docs, config, and nearby patterns relevant to the issue.
   - Cite local files and commands where they support implementation decisions.
   - Mark the issue `blocked` when required local code, credentials, generated artifacts, or external dependencies are unavailable.

5. **Plan with the rubric**
   - Read `references/planning-rubric.md` before writing the report.
   - Use the built-in rubric by default. Use `plan-with-senior-dev` only when the user explicitly asks for senior planning.
   - Mark an issue `needs-info` when the issue or local evidence lacks enough detail to plan safely.

6. **Quality-gate and report**
   - Write a Markdown report under `.scratch/github-issue-plans/<owner-repo>/<timestamp>.md`.
   - Quality-gate each issue section against `references/planning-rubric.md`.
   - A `ready-to-plan` issue must cite local evidence, implementation steps, relevant API/config/data impacts, tests, risks, and assumptions. Otherwise mark it `needs-info` or `blocked`.
   - End by summarizing the report path and top priorities in chat.

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

`GITHUB_API_URL` is optional and defaults to `https://api.github.com`.

## Safety Rules

- Do not comment on GitHub issues.
- Do not apply or remove labels.
- Do not close issues.
- Do not implement code fixes.
- Do not treat GitHub repository contents as the codebase; only the local checkout is the code source.
