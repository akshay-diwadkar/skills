---
name: build-codebase-knowledge
description: Build and use compact repository knowledge for resolver-first code navigation. Use when starting coding work in an unfamiliar or large repository, locating likely implementation ownership, or refreshing repository knowledge after a coherent change set.
---

# Build Codebase Knowledge

Use compact repository knowledge to minimize exploration and reserve the model's context and reasoning budget for implementation and verification.

1. Resolve absolute skill and repository paths.
2. Run `python scripts/cli.py status --repo-root /absolute/path/to/repo --format json`.
3. Run `build` only when artifacts are missing, invalid, or require a full rebuild; otherwise run `refresh` for a reported safe delta.
4. Run `python scripts/cli.py resolve "<task>" --repo-root /absolute/path/to/repo --phase 1 --format json`.
5. Read only the returned source slices and verify behavior in authoritative source.
6. Stop exploring when the phase question is answered. Request phase 2 or 3 only for its stated expansion trigger.
7. Perform the requested coding work. After one coherent change set, refresh with changed paths and run `validate`.

Use `--phase all` only for explicit debugging or human inspection. Do not preload maps, shards, or human-readable artifacts. Source remains authoritative.

## Commands

```bash
python scripts/cli.py build --repo-root /absolute/path/to/repo
python scripts/cli.py status --repo-root /absolute/path/to/repo --format json
python scripts/cli.py resolve "<task>" --repo-root /absolute/path/to/repo --phase 1 --format json
python scripts/cli.py refresh --repo-root /absolute/path/to/repo --changed-file /absolute/path/to/repo/src/example.py
python scripts/cli.py validate --repo-root /absolute/path/to/repo
```

`link-docs` and `generate-workflow` are explicit opt-in commands. `link-docs` updates existing instruction files only; add `--create-missing` to create one `AGENTS.md` when neither supported file exists.
