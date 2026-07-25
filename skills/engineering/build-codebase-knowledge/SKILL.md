---
name: build-codebase-knowledge
description: Build and use compact repository knowledge for resolver-first code navigation. Use when starting coding work in an unfamiliar or large repository, locating likely implementation ownership, or refreshing repository knowledge after a coherent change set.
---

# Build Codebase Knowledge

Use compact repository knowledge to minimize exploration and reserve the model's context and reasoning budget for implementation and verification.

1. Resolve absolute skill and repository paths.
2. Run `python scripts/cli.py status --repo-root /absolute/path/to/repo --format json`.
3. Build only when artifacts are missing, invalid, or require a full rebuild; otherwise refresh a safe delta.
4. Resolve phase 1 and read only its returned source slices.
5. Verify behavior in authoritative source, then stop when the phase question is answered.
6. Request phase 2 or 3 only for its stated expansion trigger.
7. Perform the coding task. After one coherent change set, refresh and validate.

Use `--phase all` only for explicit debugging or human inspection. Do not preload maps, shards, or human-readable artifacts. Source remains authoritative.

## Skill Directory Resolution

Resolve this skill directory before invoking bundled scripts. Use the resolved directory as the command base; do not assume the current working directory is the skill directory.

## Commands

```bash
python scripts/cli.py build --repo-root /absolute/path/to/repo
python scripts/cli.py status --repo-root /absolute/path/to/repo --format json
python scripts/cli.py resolve "<task>" --repo-root /absolute/path/to/repo --phase 1 --format json
python scripts/cli.py refresh --repo-root /absolute/path/to/repo --changed-file /absolute/path/to/repo/src/example.py
python scripts/cli.py validate --repo-root /absolute/path/to/repo
```

`link-docs` is explicit opt-in and updates existing instruction files only; add `--create-missing` to create one `AGENTS.md` when neither supported file exists.

To explicitly add a managed GitHub refresh workflow, provide an immutable runtime revision:

```bash
python scripts/cli.py generate-workflow --repo-root /absolute/path/to/repo \
  --revision <40-character-commit-sha>
```

This command is opt-in; none of the normal knowledge commands create or modify workflows.
