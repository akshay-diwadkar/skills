# Benchmark Evidence

This directory is the durable home for benchmark data because the repository
contract does not permit a top-level `docs/` directory. Fixture repositories,
answers, generators, schemas, baselines, and results are deliberately separate.

The reviewable version-1 slice covers shared fixture lifecycle rules and a
complete deterministic `map-codebase` comparison. Existing portfolios for the
other skills remain regression evidence; they are not presented as comparative
utility benchmarks.

Commands:

```text
python -m tools.benchmarks validate
python -m tools.benchmarks regenerate --check
python -m tools.benchmarks audit --check
python tests/skills/map-codebase/run_benchmark.py --profile representative --check
python tests/skills/map-codebase/run_benchmark.py --profile full --check
python tools/validation/measure_context_load.py --check
```

Changing a fixture repository, prompt, or answer requires a fixture-version
bump. Resolver tuning must not change frozen version-1 answers. Repository
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
