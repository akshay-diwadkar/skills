# Deterministic validation and score mapping

This repository does not claim a live model score without configured adapters.
The commands below validate checked-in guidance, worked examples, language
parsers, and the provider-neutral decision-quality harness against v5.

## Reproduce the tiny worked example

From the repository root in a POSIX-compatible shell:

```bash
work="$(mktemp -d)"
printf '%s\n' \
  'Fix normalize_name so None returns an empty string while preserving non-null normalization.' \
  > "$work/request.md"
python skills/engineering/plan-change/scripts/prepare_plan.py \
  --repo-root tests/skills/plan-change/fixtures/tiny \
  --request-file "$work/request.md" \
  --run-dir "$work/run" \
  --tier tiny \
  --intent bug-fix \
  --anchor src/names.py:normalize_name
python - "$work/tiny-example.md" <<'PY'
import re
import sys
from pathlib import Path

text = Path(
    "skills/engineering/plan-change/references/worked-examples.md"
).read_text(encoding="utf-8")
match = re.search(
    r"<!-- tiny-plan:start -->\n```markdown\n(.*?)\n```\n<!-- tiny-plan:end -->",
    text,
    re.DOTALL,
)
if match is None:
    raise SystemExit("tiny worked example block not found")
Path(sys.argv[1]).write_text(match.group(1) + "\n", encoding="utf-8")
PY
python skills/engineering/plan-change/scripts/check_plan.py \
  --tier tiny \
  --repo-root tests/skills/plan-change/fixtures/tiny \
  --baseline "$work/run/baseline.json" \
  --inventory "$work/run/inventory.json" \
  --format json \
  "$work/tiny-example.md"
python skills/engineering/plan-change/scripts/finalize_plan.py \
  --tier tiny \
  --repo-root tests/skills/plan-change/fixtures/tiny \
  --baseline "$work/run/baseline.json" \
  --inventory "$work/run/inventory.json" \
  "$work/tiny-example.md" > "$work/tiny-finalized.md"
python skills/engineering/plan-change/scripts/check_plan.py \
  --tier tiny \
  --repo-root tests/skills/plan-change/fixtures/tiny \
  --baseline "$work/run/baseline.json" \
  --inventory "$work/run/inventory.json" \
  --require-finalized \
  --format json \
  "$work/tiny-finalized.md"
```

Both checks produce:

```json
{
  "valid": true,
  "contract_version": 5,
  "diagnostics": []
}
```

The two fixture fingerprints can be independently recomputed with:

```bash
python skills/engineering/plan-change/scripts/hash_excerpt.py \
  --path tests/skills/plan-change/fixtures/tiny/src/names.py \
  --start-line 1 \
  --end-line 2
```

Passing output:

```text
excerpt-sha256: b30dd7e221cb9ea99152efd997135f3ee5eeb16868b52b422f68b2eceb7ffd62
file-sha256: ea37618d0f56f1c3b015271c76e85612106fe17d3fc6cd85f939c6c389432ca1
```

## Reproduce the standard worked example

From the repository root in a POSIX-compatible shell:

```bash
work="$(mktemp -d)"
printf '%s\n' \
  'Rename parseValue across its re-export and consumers while preserving parser behavior.' \
  > "$work/request.md"
python skills/engineering/plan-change/scripts/prepare_plan.py \
  --repo-root tests/skills/plan-change/fixtures/typescript-standard \
  --request-file "$work/request.md" \
  --run-dir "$work/run" \
  --tier standard \
  --intent refactor \
  --anchor src/parser.ts:parseValue
python - "$work/standard-example.md" <<'PY'
import re
import sys
from pathlib import Path

text = Path(
    "skills/engineering/plan-change/references/worked-examples.md"
).read_text(encoding="utf-8")
match = re.search(
    r"<!-- standard-plan:start -->\n```markdown\n(.*?)\n```\n<!-- standard-plan:end -->",
    text,
    re.DOTALL,
)
if match is None:
    raise SystemExit("standard worked example block not found")
Path(sys.argv[1]).write_text(match.group(1) + "\n", encoding="utf-8")
PY
python skills/engineering/plan-change/scripts/check_plan.py \
  --tier standard \
  --repo-root tests/skills/plan-change/fixtures/typescript-standard \
  --baseline "$work/run/baseline.json" \
  --inventory "$work/run/inventory.json" \
  --format json \
  "$work/standard-example.md"
python skills/engineering/plan-change/scripts/finalize_plan.py \
  --tier standard \
  --repo-root tests/skills/plan-change/fixtures/typescript-standard \
  --baseline "$work/run/baseline.json" \
  --inventory "$work/run/inventory.json" \
  "$work/standard-example.md" > "$work/standard-finalized.md"
python skills/engineering/plan-change/scripts/check_plan.py \
  --tier standard \
  --repo-root tests/skills/plan-change/fixtures/typescript-standard \
  --baseline "$work/run/baseline.json" \
  --inventory "$work/run/inventory.json" \
  --require-finalized \
  --format json \
  "$work/standard-finalized.md"
```

Both checks produce:

```json
{
  "valid": true,
  "contract_version": 5,
  "diagnostics": []
}
```

## Reproduce the high-risk worked example

From the repository root in a POSIX-compatible shell:

```bash
work="$(mktemp -d)"
printf '%s\n' \
  'Prevent cross-tenant feature-flag cache reuse while preserving same-tenant caching.' \
  > "$work/request.md"
python skills/engineering/plan-change/scripts/prepare_plan.py \
  --repo-root tests/skills/plan-change/fixtures/standard \
  --request-file "$work/request.md" \
  --run-dir "$work/run" \
  --tier high-risk \
  --intent bug-fix \
  --risk-domain security \
  --anchor src/flags.py:flags_for
python - "$work/high-risk-example.md" <<'PY'
import re
import sys
from pathlib import Path

text = Path(
    "skills/engineering/plan-change/references/worked-examples.md"
).read_text(encoding="utf-8")
match = re.search(
    r"<!-- high-risk-plan:start -->\n```markdown\n(.*?)\n```\n<!-- high-risk-plan:end -->",
    text,
    re.DOTALL,
)
if match is None:
    raise SystemExit("high-risk worked example block not found")
Path(sys.argv[1]).write_text(match.group(1) + "\n", encoding="utf-8")
PY
python skills/engineering/plan-change/scripts/check_plan.py \
  --tier high-risk \
  --repo-root tests/skills/plan-change/fixtures/standard \
  --baseline "$work/run/baseline.json" \
  --inventory "$work/run/inventory.json" \
  --format json \
  "$work/high-risk-example.md"
python skills/engineering/plan-change/scripts/finalize_plan.py \
  --tier high-risk \
  --repo-root tests/skills/plan-change/fixtures/standard \
  --baseline "$work/run/baseline.json" \
  --inventory "$work/run/inventory.json" \
  "$work/high-risk-example.md" > "$work/high-risk-finalized.md"
python skills/engineering/plan-change/scripts/check_plan.py \
  --tier high-risk \
  --repo-root tests/skills/plan-change/fixtures/standard \
  --baseline "$work/run/baseline.json" \
  --inventory "$work/run/inventory.json" \
  --require-finalized \
  --format json \
  "$work/high-risk-finalized.md"
```

Both checks produce:

```json
{
  "valid": true,
  "contract_version": 5,
  "diagnostics": []
}
```

## `score_plan_evaluation.py` dimensions

| Change | Targeted dimensions | Weak-model failure prevented |
|---|---|---|
| Required glossary | grounding, propagation, decisions, implementation, blueprints, verification | Makes `F` path/anchor evidence, typed `P` ownership, evidence-linked `D`, traced `CH`/`T`, and blueprint minimum/domain ownership explicit instead of requiring abbreviation inference. |
| Hash tool and hash instructions | grounding; valid parsing is a prerequisite for every dimension | Prevents stale or invented `F` fingerprints from invalidating the plan before expected paths and anchors can score. |
| Complete tiny example | grounding, propagation, decisions, implementation, verification | Demonstrates current path/anchor hashes, a material `surface`, `owner: CH-1`, `D-1` evidence, complete `CH-1`/`T-1` trace ownership, and exact observable test terms in one passing plan. |
| Bounded diagnostic repair | grounding, propagation, implementation, verification | Directs repeated failures back to the cited `F`, `P`, or `CH` evidence/ownership record and requires a named evidence gap instead of bypassing validation. |
| Concrete propagation searches | grounding, propagation, implementation | Makes callers, re-exports, fixtures, schemas/config, generators, deployment, and docs discoverable so expected surfaces receive typed dispositions and changed paths receive `CH` ownership. |

The `blueprints` scorer checks minimum count and expected domains. The glossary
therefore states both the standard/high-risk minimum and exact high-risk domain
coverage, while the tiny example correctly contains no blueprint.

## Repository validation

Run:

```bash
python -m pytest tests/skills/plan-change -q
python -m pytest tests/skills/implement-plan tests/skills/scope-issue -q
python tools/validation/validate_repository.py
git diff --check
git status --short
```

The non-Python end-to-end cases invoke `prepare_plan.py`, `check_plan.py`,
`finalize_plan.py`, and finalized `check_plan.py --require-finalized` from an
unrelated working directory for TypeScript tiny/standard and Kotlin
tiny/standard fixtures.

## Decision-quality A/B evaluation

Use `tests/skills/plan-change/evals/run_decision_quality_ab.py` with one
provider-neutral JSON adapter and distinct weaker/stronger model labels. Each
model receives the same repository and prompt under isolated `with-skill` and
`without-skill` conditions. The report exposes binary schema/grounding validity
from `check_plan.py`, held-out root-cause/minimal-fix/propagation scores, and
paired deltas. No live score movement has been measured by this checked-in
change.

Implementation-pass output:

```text
........................................................................ [ 98%]
.                                                                        [100%]
73 passed in 18.80s
Repository validation passed for 8 skills.
```

`git diff --check` produced no output and exited zero. `git status --short`
listed only the scoped files named by this change; no contract, runtime,
release-gate, or live-evaluation file was modified.
