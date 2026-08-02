# Benchmark Evidence

This directory is the durable home for benchmark data because the repository
contract does not permit a top-level `docs/` directory. Fixture repositories,
answers, generators, schemas, baselines, and results are deliberately separate.
Generated fixture repositories are committed under `benchmarks/repos`; the
generators provide reproducible updates and `regenerate --check` rejects drift.

The active version-3 evidence uses only the executable Atlas billing,
Northstar developer-portal, and SignalForge telemetry projects at fixture
version 5. `resolver-scale-stress` preserves the patterned 3k-file workload for
latency probes only. Earlier corpus metrics are not active evidence and are not
used as release comparisons because the executable v3 corpus measures different
capabilities. Resolver, ripgrep, and inventory controls still run together on
the same current repository bytes.

Commands:

```text
python -m tools.benchmarks validate
python -m tools.benchmarks regenerate --check
python -m tools.benchmarks audit --check
python tests/skills/map-codebase/run_benchmark.py --profile representative --check
python tests/skills/map-codebase/run_benchmark.py --profile full --check
python tools/validation/measure_context_load.py --check
```

For repeatable local benchmark and repository checks, create the ignored
CPython 3.11.11 environment once and invoke its interpreter explicitly:

```text
uv venv --python 3.11.11 .scratch/benchmarks/venv-map-codebase-v2
uv pip install --python .scratch/benchmarks/venv-map-codebase-v2/Scripts/python.exe -r tools/validation/release-requirements.txt
uv pip install --python .scratch/benchmarks/venv-map-codebase-v2/Scripts/python.exe pytest pytest-subtests pyyaml ruff mypy
.scratch/benchmarks/venv-map-codebase-v2/Scripts/python.exe -m pytest tests/skills/map-codebase -q
```

Delete and recreate this ignored environment whenever its requirements change.
Fixture-native restores remain separate and must use their committed lockfiles.

Changing a fixture repository, prompt, or answer requires a fixture-version
bump. Resolver tuning must preserve the frozen v3 utility, safety,
fixture-identity, and workload evidence. Observed wall time is checked against
the calibrated 2x/fixed-floor ceiling instead of exact equality.
Phase-aware oracle rationale lives outside materialized repositories under
`benchmarks/oracles/map-codebase-v3`. Benchmark answers never leak into a
fixture checkout. Repository
identity is the manifest-bound canonical path-and-content tree, not arbitrary
checkout contents; exact byte drift fails validation.

## Context-load budgets

[`context-load-budgets.json`](context-load-budgets.json) is the reviewed policy;
[`reports/context-load.json`](reports/context-load.json) is generated evidence.
Regenerate the report after changing skill instructions, phase references,
manifests, or common CLI output:

```text
python tools/validation/measure_context_load.py --write
python tools/validation/measure_context_load.py --check
```

The report uses the vendored, SHA-256-verified offline `cl100k_base` tokenizer.
It measures each top-level `SKILL.md`, successful doctor output, context needed
before the first action, phase-required and conditional references, every UTF-8
file under `references/`, and a canonical repair diagnostic. Runtime paths are
replaced with stable placeholders before tokenization.

An `established` baseline makes absolute budgets blocking. Pull-request CI also
compares the report with the trusted base revision and blocks unexpected growth
or large unexplained reductions. Exceptions must be narrow, justified by named
contract paths or mandatory safety-rule IDs, and necessary at the current
measurement; stale exceptions fail validation. Moving prose into CLI output or
another reference does not avoid measurement, and mandatory-rule reachability
continues to protect required safety and validation content.
