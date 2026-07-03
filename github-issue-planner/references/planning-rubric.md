# Planning Rubric

Use this rubric for every report. Use `plan-with-senior-dev` only when the user explicitly asks for senior planning.

## Source Boundaries

- Use GitHub only for issue metadata: issue title, body, labels, author, timestamps, URL, and comments.
- Use the local checkout as the only source for implementation details.
- Do not clone, browse, or inspect GitHub repository files for planning.
- If local code is missing or does not match the issue repository, state that mismatch in the report.

## Issue Ordering

Order plans by:

1. blockers and critical defects;
2. high-impact user-facing bugs;
3. issues with clear reproduction or acceptance criteria;
4. issues that unblock other issues;
5. lower-risk maintenance work.

## Planning Status

- `ready-to-plan`: the issue has enough detail and local code evidence to produce a decision-complete plan.
- `needs-info`: the issue lacks reproduction steps, expected behavior, scope, environment, or acceptance criteria.
- `blocked`: local code, credentials, generated artifacts, or external dependencies needed for planning are unavailable.

## Report Shape

Each issue section must include:

- issue number, title, URL, labels, author, and timestamps;
- planning status: `ready-to-plan`, `needs-info`, or `blocked`;
- summary of the issue body and relevant comments;
- local codebase findings with file references or command evidence;
- implementation plan or needs-info questions;
- verification commands and expected passing result when implementation can be planned;
- risks and assumptions.

## Plan Quality Bar

Every `ready-to-plan` issue must include:

- the required outcome in one or two sentences;
- local current-state findings with file references or command evidence;
- implementation steps in dependency order;
- public API, data shape, config, migration, or compatibility notes when relevant;
- edge cases and failure modes;
- exact tests or checks to run and expected passing result;
- a post-resolution audit follow-up that reruns `codebase-issue-auditor`, compares current findings against open audit or GitHub issues, lists resolved issue candidates with evidence, and closes them only after explicit user approval;
- assumptions that remain and why they are acceptable.

If GitHub credentials or the repository URL are missing, the follow-up should produce a local close-candidate report instead of attempting issue closure.

If any required quality-bar item is missing, the issue is not `ready-to-plan`; mark it `needs-info` or `blocked`.

## Needs-Info Handling

Do not invent missing product behavior. For `needs-info` issues, write:

- what is known from the issue;
- what local code suggests;
- the exact questions needed from the reporter or maintainer;
- any safe preparatory work that can be planned without the missing information.
