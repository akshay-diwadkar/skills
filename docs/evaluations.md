# Model Capability & Live Evaluations

To ensure that engineering skills perform reliably across different LLM backends, the repository includes provider-neutral live evaluation frameworks for key skills (`implement-with-senior-dev`, `design-codebase-with-senior-dev`, `optimize-codebase-with-senior-dev`).

---

## 1. Provider-Neutral Live Adapters

Evaluation runners separate benchmark logic from model providers. An evaluation adapter is an external executable script that:
1. Accepts a JSON execution request on `stdin` (containing target repository path, plan snapshot path, run bundle path, and skill paths).
2. Invokes the target model API or local agent runner.
3. Outputs a JSON result on `stdout` (containing generated output markdown or implementation status).

Model credentials and SDK dependencies remain inside the adapter, keeping the monorepo clean and vendor-neutral.

---

## 2. Running Live Evaluations

### `implement-with-senior-dev`

Evaluates plan execution, diff correctness, dirty worktree preservation, and verification compliance:

```bash
python tests/skills/implement-with-senior-dev/run_live_evaluations.py \
  --adapter-command "python /path/to/adapter.py" \
  --model-label "claude-3-5-sonnet" \
  --runs 3 \
  --output-dir .scratch/implement-evals
```

### `design-codebase-with-senior-dev`

Evaluates architectural assessment quality, migration safety, and read-only preservation:

```bash
python tests/skills/design-codebase-with-senior-dev/run_live_evaluations.py \
  --adapter-command "python /path/to/adapter.py" \
  --model-label "gpt-4o" \
  --runs 3 \
  --output-dir .scratch/design-evals
```

### `optimize-codebase-with-senior-dev`

Evaluates bottleneck diagnosis, optimization plan contracts, and behavior-preserving constraints:

```bash
python tests/skills/optimize-codebase-with-senior-dev/run_live_evaluations.py \
  --adapter-command "python /path/to/adapter.py" \
  --model-label "claude-3-5-sonnet" \
  --runs 3 \
  --output-dir .scratch/optimize-evals
```

---

## 3. Evaluation Thresholds & Hard Failure Rules

Live evaluations enforce strict acceptance criteria:

- **Hard Failures**: Any run that mutates read-only fixtures, crashes the adapter, corrupts dirty sentinels, or fails required verification commands results in an immediate run failure score of `0`.
- **Passing Threshold**: A skill passes evaluation for a model target if:
  1. There are **zero hard failures** across all runs.
  2. The **median score** across runs is at least **90 / 100**.
  3. No individual run score falls below **80 / 100**.

---

## 4. Default CI vs. Opt-In Evaluations

- **Default CI**: Runs deterministic unit tests, contract checks, catalog synchronization tests, repository boundary checks, and packaging verification.
- **Opt-In Live Evaluations**: Run locally or in specialized benchmark pipelines using provider adapters to evaluate new model capabilities or prompt variations.
