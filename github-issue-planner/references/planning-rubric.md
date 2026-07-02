# Planning Rubric

Use this rubric when `plan-with-senior-dev` is unavailable or the user declines to use it.

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

## Plan Quality Bar

Each plan must include:

- the required outcome in one or two sentences;
- local current-state findings with file references or command evidence;
- implementation steps in dependency order;
- public API, data shape, config, migration, or compatibility notes when relevant;
- edge cases and failure modes;
- exact tests or checks to run and expected passing result;
- assumptions that remain and why they are acceptable.

## Needs-Info Handling

Do not invent missing product behavior. For `needs-info` issues, write:

- what is known from the issue;
- what local code suggests;
- the exact questions needed from the reporter or maintainer;
- any safe preparatory work that can be planned without the missing information.
