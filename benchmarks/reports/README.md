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
every current non-map pytest lane in the CI workflows, plus a complete
non-map collection inventory, duplicate and subsumption evidence,
ownership evidence (per-node owner and owning surface, per-lane unique
protection, overlaps, gaps, cheapest owning layer, and unresolved boundary
judgments), observed failure-locality evidence, static boundary usage, and
bounded runtime evidence.

The `deferred_domains` section records `map-codebase` once as deferred to #140
and later reintegration by #230. Map test nodes, map classification cases,
map fixtures, and map-specific static boundary files are absent from the
Phase-0 inventory and runtime evidence.

The `ownership.lanes` judgment fields (`boundary_justified`, `proposed_owner`)
are `null` until a human records them in `ownership_notes` in the exceptions
file; `unresolved: true` marks them open by design.

The `failure_locality` section (`evidence: "observed-sample"`) combines two
kinds of evidence. The `distribution`, `per_lane`, and `representative`
breakdowns are derived from paths and owners: `direct` tests live in a single
skill's suite, `path-derived` tests identify their owner only via a shared
suite, `broad` tests (integration, benchmark, shared-runtime) cannot name a
specific owning contract. The `sample` list records observed diagnostics: a
small set of real tests is run against deterministic mutations of the
committed data they consume (see
`tools/validation/test-baseline-failure-samples.json`), so they fail naturally
on their own assertions and the actual pytest failure output (summary line and
failure excerpt, with machine paths normalized) is recorded per locality
class. A mutation that stops provoking a failure fails baseline generation by
design, so stale evidence is never committed silently.

Per-node `boundaries` classify each test's usage of subprocess, copytree, temp
repositories, and the semantic kinds installer (package-manager install
commands), network (HTTP/socket libraries and `curl`/`wget` subprocesses),
credential (environment reads of key/token/secret/password names plus
`keyring`/`netrc`), and external-tool (git, node, npm, go, cargo, dotnet,
gradle, and similar invocations). The report's `static` section is the same
vocabulary at file level.

`runtime.lane_executions` records executed counts and wall buckets for the
current pytest lanes. The large-repository lane carries its explicit
environment variable, while marker-gated fixture and benchmark tests remain
visible in the complete inventory without being treated as current CI lanes.
`runtime.slowest_nodes` and `runtime.slowest_groups` provide bounded duration
bucket summaries; they are diagnostic evidence, not hosted-runner thresholds.

Regenerate and commit it whenever the test system changes:

```bash
python tools/validation/build_test_baseline.py --collect-only   # structural sections
python tools/validation/build_test_baseline.py --runs 2         # structural + runtime evidence (full suite, max 3 runs)
python tools/validation/build_test_baseline.py --check          # verify committed report matches regeneration
```

- Lane manifest: `tools/validation/test-baseline-lanes.json` (mirror every pytest command in `.github/workflows`).
- Exceptions: `tools/validation/test-baseline-exceptions.json` (schema v2: `excluded` node refs, `owner_overrides` re-mapping derived owners, `ownership_notes` resolving per-lane boundary judgments; empty by default; derivation-first).
- Failure samples: `tools/validation/test-baseline-failure-samples.json` (schema v1: real test nodes plus deterministic mutations of the committed data they consume, one per locality class).
- Focused tests: `tests/repository/test_test_baseline.py`.

Post-commit gate: repository guards such as
`tests/repository/test_skill_repository.py` scan only Git-tracked files
(`git ls-files`), so a newly generated report is invisible to them until
`git add`. After `git add`, before `git push`, re-run:

```bash
python -m pytest tests/repository -q
python tools/validation/validate_repository.py
```
