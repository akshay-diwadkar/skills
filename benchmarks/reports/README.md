# Benchmark and test reports

`python -m benchmarks.run_full` and `python -m benchmarks.run_representative`
emit report-schema JSON to standard output. Capture dated runs in this directory
when comparing resolver revisions. Runtime scoring derives IDF only from the
indexed repository; resolver code must never import this package or read these
fixtures.

The pre-change `owner_precision` value in `baseline.json` is explicitly a
legacy mixed-phase metric and is not comparable to `primary_owner_precision`.

## Test baseline

`test-baseline.json` is the committed, machine-readable baseline of the
repository's test system (roadmap #218): per-lane collect-only node sets for
every pytest lane in the CI workflows, duplicate and subsumption evidence,
ownership evidence (per-node owner and owning surface, per-lane unique
protection, overlaps, gaps, cheapest owning layer, and unresolved boundary
judgments), static failure-locality evidence, static boundary usage, and
bounded runtime evidence.

The `ownership.lanes` judgment fields (`boundary_justified`, `proposed_owner`)
are `null` until a human records them in `ownership_notes` in the exceptions
file; `unresolved: true` marks them open by design.

The `failure_locality` section is derived statically
(`evidence: "derived-static"`), never from observed failures: `direct` tests
live in a single skill's suite, `path-derived` tests identify their owner only
via a shared suite, `broad` tests (integration, benchmark, shared-runtime)
cannot name a specific owning contract.

`runtime.lane_executions` records executed counts and wall buckets for every
non-benchmark pytest lane; the two benchmark lanes and the fixture-build lane
are marked `executed: false` with `reason: "benchmark-gated"` because they run
only in the prescribed benchmark environment.

Regenerate and commit it whenever the test system changes:

```bash
python tools/validation/build_test_baseline.py --collect-only   # structural sections
python tools/validation/build_test_baseline.py --runs 2         # structural + runtime evidence (full suite, max 3 runs)
python tools/validation/build_test_baseline.py --check          # verify committed report matches regeneration
```

- Lane manifest: `tools/validation/test-baseline-lanes.json` (mirror every pytest command in `.github/workflows`).
- Exceptions: `tools/validation/test-baseline-exceptions.json` (schema v2: `excluded` node refs, `owner_overrides` re-mapping derived owners, `ownership_notes` resolving per-lane boundary judgments; empty by default — derivation-first).
- Focused tests: `tests/repository/test_test_baseline.py`.

Post-commit gate: repository guards such as
`tests/repository/test_skill_repository.py` scan only Git-tracked files
(`git ls-files`), so a newly generated report is invisible to them until
`git add`. After `git add`, before `git push`, re-run:

```bash
python -m pytest tests/repository -q
python tools/validation/validate_repository.py
```
