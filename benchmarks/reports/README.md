# Resolver benchmark reports

`python -m benchmarks.run_full` and `python -m benchmarks.run_representative`
emit report-schema JSON to standard output. Capture dated runs in this directory
when comparing resolver revisions. Runtime scoring derives IDF only from the
indexed repository; resolver code must never import this package or read these
fixtures.

The pre-change `owner_precision` value in `baseline.json` is explicitly a
legacy mixed-phase metric and is not comparable to `primary_owner_precision`.
