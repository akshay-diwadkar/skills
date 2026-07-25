---
name: map-codebase
description: Build and use compact repository knowledge for resolver-first code navigation. Use when starting coding work in an unfamiliar or large repository, locating likely implementation ownership, or refreshing repository knowledge after a coherent change set.
---

# Map Codebase

Use compact machine-only repository knowledge to reduce exploration overhead while preserving source as authoritative.

1. Resolve absolute skill and repository paths.
2. Run `python scripts/cli.py status --repo-root /absolute/path/to/repo --format json`.
3. Build only when artifacts are missing, invalid, or require a full rebuild. Otherwise refresh a safe delta or metadata-only revision.
4. Resolve phase 1 and read only its returned targets; the resolver loads selected symbol shards internally.
5. Verify behavior in authoritative source, then stop when the phase question is answered.
6. Request phase 2 or 3 only for an explicit expansion trigger.
7. Perform the coding task. After one coherent change set, refresh and validate.

Use `--phase all` only for explicit debugging or human inspection. Do not preload maps or shards. Source remains authoritative.

`include_untracked = false` applies uniformly to build, status, refresh, and explicit `--changed-file` paths. The resolved knowledge directory (including `--output`) is always excluded from repository metadata, indexing, change detection, inventory fallback, and resolver searches, even when it is not ignored. `refresh` rebuilds missing, invalid, stale, and otherwise unsafe artifacts before reading a manifest. Tasks have one primary owner plus optional secondary constraints: exact indexed paths and symbols take precedence over vocabulary; mixed implementation tasks remain source-first, while test creation, direct test maintenance, and explicit test-file work are test-owned. Configuration targets use bounded active structural ranges for TOML/INI sections, YAML/JSON ancestry, and Make targets. All relationship evidence is directional and one-hop only. Expected CLI operational errors are concise stderr diagnostics with a non-zero exit status; `status` retains its machine-readable zero-exit compatibility policy.

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

The unified CLI is the preferred interface. Its successful `build` and `refresh` commands, and the standalone `scripts/build_knowledge.py` and `scripts/refresh_knowledge.py` executables, automatically ensure `AGENTS.md` and `CLAUDE.md` contain one current managed repository-knowledge reference. Importable `build_knowledge()` and `refresh_knowledge()` remain lower-level artifact-only APIs. Missing files are created, user content outside the managed block is preserved, and custom `--output` paths are reflected in the reference. Add `<!-- OPT-OUT MAP-CODEBASE -->` to either existing file to skip only that file. Agent-document updates are atomically replaced per file and rolled back across both files on a failed commit; knowledge artifacts remain available when finalization fails. `link-docs` remains available to explicitly repair or reapply the references; it always creates missing supported files and accepts `--create-missing` as a compatibility no-op.

To explicitly add a managed GitHub refresh workflow, provide an immutable runtime revision:

```bash
python scripts/cli.py generate-workflow --repo-root /absolute/path/to/repo \
  --revision <40-character-commit-sha>
```

This command is opt-in; none of the normal knowledge commands create or modify workflows.
