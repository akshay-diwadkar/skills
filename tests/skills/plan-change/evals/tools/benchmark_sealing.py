#!/usr/bin/env python3
"""Compare the removed v5 machine pipeline with the v6 sealing microbenchmark."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import platform
import statistics
import sys
import tempfile
import time
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[5]


def _load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load benchmark module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


HELPERS = _load(ROOT / "tests" / "skills" / "plan-change" / "v6_helpers.py", "plan_change_v6_helpers")
V5_BASELINE = _load(Path(__file__).with_name("v5_machine_baseline.py"), "plan_change_v5_machine_baseline")
sys.path.insert(0, str(ROOT / "tools"))
import plan_contract_runtime as V5_RUNTIME  # type: ignore[import-not-found]  # noqa: E402


def _load_v5_scaffold() -> ModuleType:
    scripts = ROOT / "skills" / "engineering" / "implement-plan" / "scripts"
    sys.path.insert(0, str(scripts))
    previous = sys.modules.get("plan_runtime")
    sys.modules["plan_runtime"] = V5_RUNTIME
    try:
        return _load(scripts / "plan_contract.py", "plan_change_v5_scaffold")
    finally:
        if previous is None:
            sys.modules.pop("plan_runtime", None)
        else:
            sys.modules["plan_runtime"] = previous
        sys.path.remove(str(scripts))


V5_SCAFFOLD = _load_v5_scaffold()


def _percentile95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, int(len(ordered) * 0.95 + 0.999) - 1))]


def _timing(values: list[float]) -> dict[str, float]:
    return {"median": statistics.median(values), "p95": _percentile95(values)}


def _make_repo(root: Path) -> Path:
    (root / "src").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / "src" / "target.py").write_text(
        "def target(raw: str) -> str:\n    return raw.strip()\n", encoding="utf-8"
    )
    (root / "tests" / "test_target.py").write_text(
        "from src.target import target\n\ndef test_target():\n    assert target(' x ') == 'x'\n",
        encoding="utf-8",
    )
    return root


def _v5_draft(repo: Path, tier: str) -> tuple[str, str]:
    domains = ["security"] if tier == "high-risk" else []
    intent = "bug-fix" if tier == "tiny" else "refactor"
    signals = [] if tier == "tiny" else ["transitive-consumers"]
    scaffold = V5_SCAFFOLD.render_scaffold(tier, intent, domains, signals)
    source = repo / "src" / "target.py"
    excerpt = "def target(raw: str) -> str:\n"
    replacements = {
        "REPLACE_CURRENT_PATH": "src/target.py",
        "REPLACE_CURRENT_RANGE": "1-1",
        "REPLACE_CURRENT_ANCHOR": "target",
        "REPLACE_CURRENT_HASH": hashlib.sha256(excerpt.encode()).hexdigest(),
        "REPLACE_CURRENT_FILE_HASH": hashlib.sha256(source.read_bytes()).hexdigest(),
        "REPLACE_EXACT_SIGNATURE": "raw: str",
        "REPLACE_EXACT_RETURN": "str",
        "REPLACE_TARGETED_TEST.py": "test_target.py",
        "REPLACE_security.py": "test_security.py",
    }
    draft = scaffold
    for old, new in replacements.items():
        draft = draft.replace(old, new)
    return scaffold, draft


def _v6_draft(tier: str) -> str:
    metadata = {
        "tiny": '{"intent":"bug-fix","tier":"tiny","risk_domains":[]}',
        "standard": '{"intent":"refactor","tier":"standard","risk_domains":[]}',
        "high-risk": '{"intent":"bug-fix","tier":"high-risk","risk_domains":["security"]}',
    }[tier]
    boundaries = ""
    if tier == "high-risk":
        boundaries = """
## Boundaries and Risks
B-1: class: trusted input boundary | evidence: F-1 | flow: caller input -> authorization decision -> target normalization
R-1: severity: P1 | owner: CH-1 | tests: T-1 | risk: unauthorized input could cross the normalization boundary
"""
    return f"""# Update the target behavior

<!-- plan-contract: 6 -->
<!-- plan-metadata: {metadata} -->

## Outcome
SC-1: given: a padded target value | when: target processes the input | then: it returns the stripped value | unchanged: the public string result remains stable

## Evidence
F-1: kind: source | path: src/target.py | lines: 1-2 | anchor: target | claim: target owns the current string normalization

## Implementation
CH-1: path: src/target.py | anchor: target | status: existing | evidence: F-1 | change: preserve exact string normalization while applying the requested tier-specific implementation update | locality: shared | reversibility: reversible
{boundaries}
## Verification
T-1: covers: SC-1, CH-1 | given: padded and plain target values | when: targeted tests execute | then: both values retain the exact normalized result | command: python -m pytest tests/test_target.py -q
"""


def _measure(iterations: int) -> dict[str, Any]:
    tiers = ("tiny", "standard", "high-risk")
    samples: dict[str, dict[str, list[float]]] = {
        tier: {"prepare": [], "validate": [], "finalize": [], "aggregate": [], "seal": []}
        for tier in tiers
    }
    operations: dict[str, Any] = {}
    with tempfile.TemporaryDirectory(prefix="plan-change-machine-benchmark-") as temporary:
        root = Path(temporary)
        repo = _make_repo(root / "repo")
        for tier in tiers:
            request = root / f"{tier}-request.md"
            request.write_text(f"Apply the equivalent {tier} target change.\n", encoding="utf-8")
            v5_scaffold, v5_draft = _v5_draft(repo, tier)
            v6_path = root / f"{tier}-v6.md"
            v6_path.write_text(_v6_draft(tier), encoding="utf-8")
            for iteration in range(iterations):
                run_dir = root / "v5-runs" / tier / str(iteration)
                started = time.perf_counter()
                baseline, _inventory = V5_BASELINE.prepare(
                    repo, request, run_dir, v5_scaffold, V5_RUNTIME.snapshot
                )
                prepare_seconds = time.perf_counter() - started

                started = time.perf_counter()
                plan, diagnostics = V5_RUNTIME.validate_plan(v5_draft, repo, baseline=baseline)
                validate_seconds = time.perf_counter() - started
                if plan is None or diagnostics:
                    raise RuntimeError("v5 benchmark draft failed validation: " + "; ".join(map(str, diagnostics)))

                started = time.perf_counter()
                V5_RUNTIME.finalized_text(v5_draft, repo, baseline=baseline)
                finalize_seconds = time.perf_counter() - started

                started = time.perf_counter()
                sealed = HELPERS.RUNTIME.seal_plan(repo, request, v6_path)
                seal_seconds = time.perf_counter() - started

                samples[tier]["prepare"].append(prepare_seconds)
                samples[tier]["validate"].append(validate_seconds)
                samples[tier]["finalize"].append(finalize_seconds)
                samples[tier]["aggregate"].append(
                    prepare_seconds + validate_seconds + finalize_seconds
                )
                samples[tier]["seal"].append(seal_seconds)
            operations[tier] = sealed.counters
    comparison = {
        tier: {
            "v5": {
                "prepare": _timing(samples[tier]["prepare"]),
                "validate": _timing(samples[tier]["validate"]),
                "finalize": _timing(samples[tier]["finalize"]),
                "aggregate_machine_pipeline": _timing(samples[tier]["aggregate"]),
            },
            "v6": {"seal": _timing(samples[tier]["seal"])},
        }
        for tier in tiers
    }
    return {
        "comparison": comparison,
        "v6_timings": {tier: _timing(samples[tier]["seal"]) for tier in tiers},
        "operations": operations,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=30)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.iterations < 1:
        parser.error("--iterations must be positive")
    measured = _measure(args.iterations)
    command = (
        "python tests/skills/plan-change/evals/tools/benchmark_sealing.py "
        f"--iterations {args.iterations}"
    )
    if args.output:
        command += f" --output {args.output.as_posix()}"
    report = {
        "schema_version": 2,
        "methodology": {
            "benchmark_type": "machine-pipeline microbenchmark",
            "same_fixture_request_environment_and_timing_boundary": True,
            "excluded": ["agent exploration", "agent drafting", "tool-call accounting", "token accounting"],
            "end_to_end_native_agent_parity": "not_measured",
            "parity_requires": [
                "same model and effort",
                "same repository and request",
                "same environment",
                "complete tool-call accounting",
                "complete token accounting",
            ],
        },
        "historical_v5_suite_baseline": {
            "label": "historical full test-suite wall time; not comparable to microbenchmark timings",
            "command": "python -m pytest tests/skills/plan-change -q --durations=10",
            "passed_tests": 102,
            "wall_seconds": 69.77,
            "comparable_to_machine_pipeline": False,
        },
        "machine_pipeline_comparison": {
            "command": command,
            "iterations": args.iterations,
            "timings_seconds": measured["comparison"],
        },
        "v6_sealing_microbenchmark": {
            "label": "v6 sealing only; excludes repository exploration and agent work",
            "iterations": args.iterations,
            "timings_seconds": measured["v6_timings"],
            "operation_counts": measured["operations"],
        },
        "environment": {
            "date": "2026-08-01",
            "platform": platform.platform(),
            "python": platform.python_version(),
            "timing_gate": "informational here; the dedicated 50,003-file job enforces the under-three-second seal gate",
        },
    }
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
