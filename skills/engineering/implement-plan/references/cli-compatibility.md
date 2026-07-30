# Implement Plan Direct CLI Compatibility

Use these lower-level entry points when integrating without the common
stateful CLI. Keep the plan and run bundle outside the installed skill. Use
ignored repository storage only after confirming it with `git check-ignore`.

## Scaffold

```bash
python /absolute/skill-root/scripts/scaffold_implementation.py \
  --repo-root /absolute/path/to/repository \
  --plan /absolute/path/to/finalized-plan.md \
  --output /absolute/path/to/run/implementation.json
```

The scaffold preserves exact plan normalization, repository identity, dirty
state, target hashes, and immutable before-copies under `snapshots/`. Direct
integrations must apply the dirty-target authorization rule before editing.

## Record optional review diffs

After authoritative before/after hashes have been recorded:

```bash
python /absolute/skill-root/scripts/record_change_diff.py \
  --repo-root /absolute/path/to/repository \
  --bundle /absolute/path/to/run/implementation.json \
  --change-index <zero-based-index>
```

The unified diff is review metadata and never replaces hashes.

## Validate and finalize

```bash
python /absolute/skill-root/scripts/check_implementation.py \
  --repo-root /absolute/path/to/repository \
  --plan /absolute/path/to/finalized-plan.md \
  --format json \
  /absolute/path/to/run/implementation.json

python /absolute/skill-root/scripts/finalize_implementation.py \
  --repo-root /absolute/path/to/repository \
  --plan /absolute/path/to/finalized-plan.md \
  /absolute/path/to/run/implementation.json

python /absolute/skill-root/scripts/check_implementation.py \
  --repo-root /absolute/path/to/repository \
  --plan /absolute/path/to/finalized-plan.md \
  --format json \
  --require-complete \
  --require-receipt \
  /absolute/path/to/run/implementation.json
```

The first validation command preserves its historical behavior and may inspect
an in-progress bundle. The two new flags are optional strict gates for
completion integrations. Never claim completion unless the final command
passes against the current workspace and exact plan.
