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
```

Changing a fixture repository, prompt, or answer requires a fixture-version
bump. Resolver tuning must not change frozen version-1 answers. Repository
identity is the manifest-bound canonical path-and-content tree, not arbitrary
checkout contents; exact byte drift fails validation.
