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
static boundary usage, and bounded runtime evidence.

Regenerate and commit it whenever the test system changes:

```bash
python tools/validation/build_test_baseline.py --collect-only   # structural sections
python tools/validation/build_test_baseline.py --runs 2         # structural + runtime evidence (full suite, max 3 runs)
python tools/validation/build_test_baseline.py --check          # verify committed report matches regeneration
```

- Lane manifest: `tools/validation/test-baseline-lanes.json` (mirror every pytest command in `.github/workflows`).
- Exceptions: `tools/validation/test-baseline-exceptions.json` (empty by default; derivation-first).
- Focused tests: `tests/repository/test_test_baseline.py`.

Post-commit gate: repository guards such as
`tests/repository/test_skill_repository.py` scan only Git-tracked files
(`git ls-files`), so a newly generated report is invisible to them until
`git add`. After `git add`, before `git push`, re-run:

```bash
python -m pytest tests/repository -q
python tools/validation/validate_repository.py
```
