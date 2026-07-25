# Build Codebase Knowledge

`build-codebase-knowledge` creates compact repository artifacts and resolves coding tasks into small, evidence-backed read phases.

```bash
python skills/engineering/build-codebase-knowledge/scripts/cli.py status --repo-root /absolute/path/to/repo --format json
python skills/engineering/build-codebase-knowledge/scripts/cli.py resolve "fix auth token parsing" --repo-root /absolute/path/to/repo --phase 1 --format json
python skills/engineering/build-codebase-knowledge/scripts/cli.py refresh --repo-root /absolute/path/to/repo --changed-file /absolute/path/to/repo/src/auth.py
```

Builds are side-effect-safe: they write only under the configured knowledge directory. Use `link-docs` or `generate-workflow` explicitly when those integrations are wanted.
