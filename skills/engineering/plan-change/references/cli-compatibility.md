# Plan Change Direct CLI Compatibility

Use these lower-level commands when integrating without the common stateful
CLI. They remain public and resolve imports relative to the installed skill.
Pass absolute paths and keep the run directory outside the target repository.

## Prepare

```bash
python /absolute/skill-root/scripts/prepare_plan.py \
  --repo-root /absolute/path/to/repository \
  --request-file /absolute/path/to/request.md \
  --run-dir /absolute/path/to/run \
  --tier <tiny|standard|high-risk> \
  --intent <feature|bug-fix|refactor> \
  --anchor <repository/path[:symbol]> \
  [--risk-domain <domain> ...]
```

`scaffold_plan.py` remains available when only a contract scaffold is needed.
Use `snapshot_plan.py` and `plan_inventory.py` through their documented
arguments when integrating the preparation steps separately.

## Hash evidence

```bash
python /absolute/skill-root/scripts/hash_excerpt.py \
  --path /absolute/path/to/repository/file \
  --start-line <first-line> \
  --end-line <last-line>
```

Never estimate either evidence hash. Recompute both hashes after any content
or inclusive line-range change.

## Validate and finalize

```bash
python /absolute/skill-root/scripts/check_plan.py \
  --tier <tiny|standard|high-risk> \
  --repo-root /absolute/path/to/repository \
  --baseline /absolute/path/to/run/baseline.json \
  --inventory /absolute/path/to/run/inventory.json \
  --format json \
  /absolute/path/to/run/draft.md

python /absolute/skill-root/scripts/finalize_plan.py \
  --tier <tiny|standard|high-risk> \
  --repo-root /absolute/path/to/repository \
  --baseline /absolute/path/to/run/baseline.json \
  --inventory /absolute/path/to/run/inventory.json \
  /absolute/path/to/run/draft.md

python /absolute/skill-root/scripts/check_plan.py \
  --tier <tiny|standard|high-risk> \
  --repo-root /absolute/path/to/repository \
  --baseline /absolute/path/to/run/baseline.json \
  --inventory /absolute/path/to/run/inventory.json \
  --require-finalized \
  --format json \
  /absolute/path/to/run/final.md
```

Do not finalize until ordinary validation passes. Preserve the finalizer's
exact stdout; only the finalized validation run proves the v5 receipt and
current repository binding.

Count repair attempts separately by diagnostic category. Re-read the named
evidence or ownership record before a fourth failure in one category, and
stop with the specific evidence gap after five failures. Never downgrade the
tier, suppress a diagnostic, or change ownership only to obtain a pass.
