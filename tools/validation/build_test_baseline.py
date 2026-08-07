#!/usr/bin/env python3
"""Build the canonical repository test-system baseline (roadmap #218).

Derives a machine-readable baseline of the repository's test system:

- exact collected node sets for every required CI lane command (pytest
  ``--collect-only``);
- per-node suite, layer, domain, markers, and classification derived from
  paths, markers, and the committed exceptions file;
- duplicate evidence by exact node identity across lanes, plus subsumption
  and source-path rollups;
- runtime boundary evidence (subprocess, copy volume, fixture hotspots,
  duration buckets) via ``test_baseline_recorder`` when executed;
- static AST boundary evidence for files the runtime pass does not exercise.

The committed report is ``benchmarks/reports/test-baseline.json``. The
``--check`` mode regenerates the structural sections and fails on drift, so
determinism and exceptions validity are assertable without re-running the
suite.

Usage::

    python tools/validation/build_test_baseline.py --collect-only
    python tools/validation/build_test_baseline.py --runs 3
    python tools/validation/build_test_baseline.py --check
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[2]
LANES_PATH = ROOT / "tools" / "validation" / "test-baseline-lanes.json"
EXCEPTIONS_PATH = ROOT / "tools" / "validation" / "test-baseline-exceptions.json"
REPORT_PATH = ROOT / "benchmarks" / "reports" / "test-baseline.json"
RECORDER_PLUGIN = "test_baseline_recorder"
RECORDER_PATH = ROOT / "tools" / "validation" / f"{RECORDER_PLUGIN}.py"
TESTS_ROOT = ROOT / "tests"

BUCKET_EDGES = (0.0, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0)
BUCKET_LABELS = tuple(f"{edge:g}s" for edge in BUCKET_EDGES)

VALIDATOR_LANES: list[dict[str, Any]] = [
    {
        "id": "pre-release.validate-runtime-discovery",
        "workflow": "pre-release.yml",
        "job": "validate-release",
        "command": "python tools/validation/validate_runtime_discovery_policy.py",
        "kind": "validator",
    },
    {
        "id": "pre-release.validate-repository",
        "workflow": "pre-release.yml",
        "job": "validate-release",
        "command": "python tools/validation/validate_repository.py",
        "kind": "validator",
    },
    {
        "id": "quality.validate-repository",
        "workflow": "quality.yml",
        "job": "quality",
        "command": "python tools/validation/validate_repository.py",
        "kind": "validator",
    },
    {
        "id": "plan-change-hardening.validate-repository",
        "workflow": "plan-change-hardening.yml",
        "job": "verify",
        "command": "python tools/validation/validate_repository.py",
        "kind": "validator",
    },
    {
        "id": "quality.context-load",
        "workflow": "quality.yml",
        "job": "context-load",
        "command": "python tools/validation/measure_context_load.py --check",
        "kind": "validator",
    },
    {
        "id": "quality.cross-platform.context-load",
        "workflow": "quality.yml",
        "job": "cross-platform",
        "command": "python tools/validation/measure_context_load.py --check",
        "kind": "validator",
        "matrix_cells": [
            "ubuntu-latest py3.11",
            "ubuntu-latest py3.12",
            "windows-latest py3.11",
            "windows-latest py3.12",
            "macos-latest py3.11",
            "macos-latest py3.12",
        ],
    },
    {
        "id": "quality.lint",
        "workflow": "quality.yml",
        "job": "quality",
        "commands": ["ruff check .", "python tools/validation/run_mypy.py"],
        "kind": "lint",
    },
    {
        "id": "plan-change-hardening.lint",
        "workflow": "plan-change-hardening.yml",
        "job": "verify",
        "commands": ["ruff check .", "python tools/validation/run_mypy.py"],
        "kind": "lint",
    },
    {
        "id": "quality.npx-output",
        "workflow": "quality.yml",
        "job": "npx-install",
        "command": "python tools/validation/validate_npx_output.py <skills-list>",
        "kind": "installer",
        "matrix_cells": ["codex"],
    },
    {
        "id": "quality.npx-install",
        "workflow": "quality.yml",
        "job": "npx-install",
        "command": "python tools/validation/validate_skills_cli_install.py --agent <agent>",
        "kind": "installer",
        "matrix_cells": ["claude-code", "codex", "github-copilot"],
    },
    {
        "id": "quality.fixture-lifecycle",
        "workflow": "quality.yml",
        "job": "fixture-contract",
        "commands": [
            "python -m tools.benchmarks validate",
            "python -m tools.benchmarks regenerate --check",
            "python -m tools.benchmarks audit --check",
        ],
        "kind": "fixture-validator",
        "matrix_cells": ["ubuntu-latest", "windows-latest"],
    },
    {
        "id": "benchmarks.fixture-lifecycle",
        "workflow": "benchmarks.yml",
        "job": "map-codebase-full",
        "commands": [
            "python -m tools.benchmarks validate",
            "python -m tools.benchmarks regenerate --check",
            "python -m tools.benchmarks audit --check",
        ],
        "kind": "fixture-validator",
    },
    {
        "id": "fixture-builds.native",
        "workflow": "fixture-builds.yml",
        "job": "build-realistic-fixtures",
        "commands": [
            "python -m compileall -q benchmarks/repos/schema-migration-service/services",
            "python -m pytest benchmarks/repos/schema-migration-service/tests",
            "npm ci --ignore-scripts / npm run build / npm test",
            "sh ./gradlew --no-daemon test",
            "go test ./...",
            "cargo test --locked",
            "dotnet restore --locked-mode / dotnet test / dotnet run --no-restore",
        ],
        "kind": "external-tool",
    },
]


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _bucket(seconds: float) -> str:
    for index, edge in enumerate(BUCKET_EDGES):
        if seconds < edge:
            return BUCKET_LABELS[max(index - 1, 0)]
    return f">{BUCKET_EDGES[-1]:g}s"


def _bucket_index(label: str) -> int:
    try:
        return BUCKET_LABELS.index(label)
    except ValueError:
        return len(BUCKET_LABELS) - 1


def _median_bucket(labels: Sequence[str]) -> str:
    indices = sorted(_bucket_index(label) for label in labels)
    return BUCKET_LABELS[indices[(len(indices) - 1) // 2]]


def _median(values: Sequence[int]) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    return ordered[(len(ordered) - 1) // 2]


def _head_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False
    )
    return result.stdout.strip() or "unknown"


def _node_file(node_id: str) -> str:
    return node_id.split("::", 1)[0]


def _rel(path: Path | str, base: Path) -> str:
    return str(os.path.relpath(Path(path), base)).replace(os.sep, "/")


def _suite_of(node_id: str) -> str:
    file_path = _node_file(node_id)
    relative = _rel(file_path, TESTS_ROOT)
    if relative.startswith(".."):
        return file_path
    parts = Path(relative).parts
    if parts and parts[0] == "skills" and len(parts) >= 3:
        return f"skills/{parts[1]}"
    return parts[0] if parts else file_path


def _layer_for_file(relative: str) -> str:
    if relative.startswith(".."):
        return "external-fixture"
    lowered = relative.lower()
    if lowered.startswith("skills") and (
        "/evals/" in lowered
        or "/eval/" in lowered
        or "/fixtures/" in lowered
        or "/repos/" in lowered
        or lowered.endswith(("worked-example-fixtures", "static-regression-cases"))
    ):
        return "fixture-repository"
    if lowered.startswith("skills"):
        return "skill-local"
    if lowered.startswith("repository"):
        return "repository-policy"
    if lowered.startswith("shared"):
        return "shared-runtime"
    if lowered.startswith("skill_protocol"):
        return "shared-protocol"
    if lowered.startswith("classification"):
        return "classification"
    if lowered.startswith("integration"):
        return "installed-execution"
    if lowered.startswith("benchmarks"):
        return "benchmark-fixture"
    return "unclassified"


def _derive_layer(node_id: str) -> str:
    relative = _rel(_node_file(node_id), TESTS_ROOT)
    if relative.startswith(".."):
        return "external-fixture"
    return _derive_layer_from_path(relative)


def _derive_layer_from_path(relative: str) -> str:
    lowered = relative.lower().replace(os.sep, "/")
    if lowered.startswith("skills") and any(
        marker in lowered
        for marker in (
            "/evals/",
            "/eval/",
            "/fixtures/",
            "/repos/",
            "/worked-example-fixtures",
            "/static-regression-cases",
        )
    ):
        return "fixture-repository"
    if lowered.startswith("skills"):
        return "skill-local"
    if lowered.startswith("repository"):
        return "repository-policy"
    if lowered.startswith("shared"):
        return "shared-runtime"
    if lowered.startswith("skill_protocol"):
        return "shared-protocol"
    if lowered.startswith("classification"):
        return "classification"
    if lowered.startswith("integration"):
        return "installed-execution"
    if lowered.startswith("benchmarks"):
        return "benchmark-fixture"
    return "unclassified"


def _derive_domain(node_id: str) -> str:
    parts = Path(_rel(_node_file(node_id), TESTS_ROOT)).parts
    if parts and parts[0] == "skills" and len(parts) >= 2:
        return parts[1]
    return "repository"


def _classify(node_id: str, markers: Sequence[str], lanes: Sequence[str]) -> str:
    if "fixtures" in markers:
        return "fixture-integrity"
    if "benchmark" in markers or "benchmark_slow" in markers:
        return "benchmark-evidence"
    if _derive_layer(node_id) == "installed-execution":
        return "compatibility-check"
    if _derive_layer(node_id) == "fixture-repository":
        return "fixture-composition"
    if len(lanes) > 1:
        return "suspected-duplicate"
    return "primary-proof"


def _run_pytest(
    args: Sequence[str],
    recorder_out: str | None,
    extra_env: dict[str, str] | None = None,
    timeout_seconds: int = 3600,
) -> tuple[int, str]:
    command = [sys.executable, "-m", "pytest", *args, "-p", "no:cacheprovider"]
    env = dict(os.environ)
    validation_dir = str(ROOT / "tools" / "validation")
    env["PYTHONPATH"] = validation_dir + os.pathsep + env.get("PYTHONPATH", "")
    if recorder_out:
        env["TEST_BASELINE_RECORDER_OUT"] = recorder_out
        command.extend(["-p", RECORDER_PLUGIN])
    if extra_env:
        env.update(extra_env)
    result = subprocess.run(
        command, cwd=ROOT, capture_output=True, text=True, env=env, timeout=timeout_seconds
    )
    return result.returncode, result.stdout + result.stderr


def collect_lane(lane: dict[str, Any], recorder_out: str | None) -> dict[str, Any]:
    args = list(lane["args"])
    started = time.monotonic()
    returncode, output = _run_pytest([*args, "--collect-only", "-q"], recorder_out)
    elapsed = time.monotonic() - started
    node_ids = sorted(line.strip() for line in output.splitlines() if line.startswith("tests/"))
    summary: dict[str, Any] = {"returncode": returncode, "elapsed_seconds_bucket": _bucket(elapsed)}
    collected_match = re.search(r"(\d+)\s+tests collected", output)
    if collected_match:
        summary["tests_collected"] = int(collected_match.group(1))
    deselected_match = re.search(r"(\d+)\s+tests deselected", output)
    if deselected_match:
        summary["tests_deselected"] = int(deselected_match.group(1))
    if returncode != 0 or "ERROR" in output:
        summary["error"] = output[-2000:]
    summary["node_ids"] = node_ids
    return summary


def static_scan(root: Path) -> dict[str, Any]:
    kind_of: dict[str, list[str]] = defaultdict(list)
    scan_root = root / "tests"
    for path in sorted(scan_root.rglob("test_*.py")):
        if "__pycache__" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                base, attr = func.value.id, func.attr
                if base == "subprocess" and attr in ("run", "Popen", "call", "check_call", "check_output"):
                    kind_of[attr].append(_rel(path, root))
                elif base == "shutil" and attr.startswith(("copy", "copytree", "rmtree")):
                    kind_of[attr].append(_rel(path, root))
                elif base == "os" and attr in ("system", "popen", "spawn"):
                    kind_of["os-spawn"].append(_rel(path, root))
                elif base in ("requests", "urllib", "socket", "httpx"):
                    kind_of["network"].append(_rel(path, root))
    static: dict[str, Any] = {}
    for kind, files in sorted(kind_of.items()):
        static[kind] = sorted(set(files))
    return static


def _scan_in_process_validators(root: Path) -> list[str]:
    imports: list[str] = []
    for path in sorted((root / "tests").rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for marker in (
            "import validate_",
            "import run_mypy",
            "import tools.benchmarks",
            "from tools.benchmarks",
            "import benchmarks",
            "from benchmarks",
        ):
            if marker in text:
                imports.append(f"{_rel(path, root)}: {marker[7:]}")
                break
    return imports


def _skills_without_tests(root: Path) -> list[str]:
    skills = {
        skill.name
        for domain in sorted((root / "skills").iterdir())
        if domain.is_dir()
        for skill in sorted(domain.iterdir())
        if skill.is_dir() and (skill / "SKILL.md").is_file()
    }
    with_tests = {path.name for path in (root / "tests" / "skills").iterdir() if path.is_dir()}
    return sorted(skills - with_tests)


def _collect_ignore_findings(root: Path) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for path in sorted((root / "tests").rglob("conftest.py")):
        text = path.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            stripped = line.strip()
            if "collect_ignore" in stripped:
                findings.append(
                    {"file": _rel(path, root), "line": stripped[:120]}
                )
    return findings


def build_structural(root: Path, lanes_path: Path, exceptions_path: Path) -> dict[str, Any]:
    lanes_manifest = _load_json(lanes_path)
    exceptions = _load_json(exceptions_path)
    if lanes_manifest.get("schema_version") != 1:
        raise ValueError(f"{lanes_path}: unsupported lane manifest schema version")
    if exceptions.get("schema_version") != 1:
        raise ValueError(f"{exceptions_path}: unsupported exceptions schema version")

    lanes: list[dict[str, Any]] = []
    all_markers: dict[str, list[str]] = {}
    all_nodes: dict[str, set[str]] = {}
    with tempfile.TemporaryDirectory() as work:
        for lane in lanes_manifest["lanes"]:
            recorder_out = os.path.join(work, "markers.json")
            collected = collect_lane(lane, recorder_out)
            if collected.get("error"):
                raise RuntimeError(f"lane {lane['id']} failed: {collected['error']}")
            lane_id: str = lane["id"]
            nodes = collected["node_ids"]
            all_nodes[lane_id] = set(nodes)
            entry = {
                "id": lane_id,
                "workflow": lane["workflow"],
                "job": lane["job"],
                "args": list(lane["args"]),
                "matrix_cells": list(lane.get("matrix_cells", [])),
                "env_gated": bool(lane.get("env_gated", False)),
                "node_count": len(nodes),
                "node_ids": nodes,
            }
            if entry["matrix_cells"]:
                entry["matrix_executions"] = len(nodes) * len(entry["matrix_cells"])
            if "error" in collected:
                entry["error"] = collected["error"]
            lanes.append(entry)
            markers_path = Path(recorder_out)
            if markers_path.exists():
                markers = _load_json(markers_path).get("markers", {})
                for node_id, names in markers.items():
                    if node_id in all_nodes[lane_id]:
                        all_markers[node_id] = sorted(set(all_markers.get(node_id, [])) | set(names))

    static = static_scan(root)

    inventory: list[dict[str, Any]] = []
    for node_id in sorted(set().union(*all_nodes.values())):
        lanes_here = sorted(lane_id for lane_id, nodes in all_nodes.items() if node_id in nodes)
        markers = sorted(all_markers.get(node_id, []))
        classification = _classify(node_id, markers, lanes_here)
        inventory.append(
            {
                "node_id": node_id,
                "file": _node_file(node_id),
                "suite": _suite_of(node_id),
                "layer": _derive_layer(node_id),
                "domain": _derive_domain(node_id),
                "markers": markers,
                "classification": classification,
                "lanes": lanes_here,
            }
        )

    overlap_pairs: list[dict[str, Any]] = []
    subsumptions: list[dict[str, Any]] = []
    lane_ids = sorted(all_nodes)
    for index, lane_a in enumerate(lane_ids):
        for lane_b in lane_ids[index + 1 :]:
            overlap = sorted(all_nodes[lane_a] & all_nodes[lane_b])
            if not overlap:
                continue
            overlap_pairs.append(
                {"lane_a": lane_a, "lane_b": lane_b, "overlap_count": len(overlap), "node_ids": overlap}
            )
            if len(all_nodes[lane_a]) == len(overlap):
                subsumptions.append({"subset": lane_a, "superset": lane_b, "overlap_count": len(overlap)})
            if len(all_nodes[lane_b]) == len(overlap):
                subsumptions.append({"subset": lane_b, "superset": lane_a, "overlap_count": len(overlap)})

    source_path_rollup: dict[str, Any] = {}
    by_file: dict[str, dict[str, Any]] = defaultdict(lambda: {"lanes": set(), "count": 0})
    for row in inventory:
        entry = by_file[row["file"]]
        entry["lanes"].update(row["lanes"])
        entry["count"] += 1
    for file_path, entry in sorted(by_file.items()):
        if len(entry["lanes"]) > 1:
            source_path_rollup[file_path] = {
                "count": entry["count"],
                "lanes": sorted(entry["lanes"]),
            }

    excluded: list[dict[str, Any]] = []
    for entry in exceptions.get("excluded", []):
        node_id = entry.get("node_id")
        if node_id and node_id in all_markers:
            excluded.append({"node_id": node_id, "reason": entry.get("reason", "")})

    return {
        "schema_version": 1,
        "repository": {
            "head_commit": _head_commit(),
            "python": sys.version.split()[0],
            "root": ".",
        },
        "lanes": lanes,
        "validators": VALIDATOR_LANES,
        "inventory": inventory,
        "duplicates": {
            "overlap_pairs": overlap_pairs,
            "subsumptions": subsumptions,
            "source_path_rollup": source_path_rollup,
        },
        "static": static,
        "in_process_validator_imports": _scan_in_process_validators(root),
        "skills_without_tests": _skills_without_tests(root),
        "collect_ignore_findings": _collect_ignore_findings(root),
        "exclusions": excluded,
    }


def _normalize_detail(detail: str) -> str:
    normalized = detail.replace(os.sep, "/")
    root_forward = str(ROOT).replace(os.sep, "/")
    normalized = normalized.replace(root_forward, ".")
    tempdir = tempfile.gettempdir().replace(os.sep, "/")
    tempdir_real = os.path.realpath(tempfile.gettempdir()).replace(os.sep, "/")
    for candidate in (tempdir, tempdir_real):
        if normalized.startswith(candidate):
            normalized = "%TEMP%" + normalized[len(candidate) :]
            break
    return normalized[:300]


def _merge_recorder(run_files: Sequence[Path]) -> dict[str, Any]:
    nodes: dict[str, dict[str, Any]] = {}
    fixtures: Counter[str] = Counter()
    fixture_buckets: dict[str, list[str]] = defaultdict(list)
    boundaries: list[dict[str, Any]] = []
    boundary_node_files: set[str] = set()
    for path in run_files:
        if not path.exists():
            continue
        data = _load_json(path)
        for node_id, values in data.get("nodes", {}).items():
            entry = nodes.setdefault(
                node_id,
                {"bucket_labels": [], "subprocess_counts": [], "copy_volume": [], "copy_counts": []},
            )
            entry["bucket_labels"].append(str(values.get("bucket", ">120s")))
            entry["subprocess_counts"].append(int(values.get("subprocess", 0)))
            entry["copy_volume"].append(int(values.get("copy_bytes", 0)))
            entry["copy_counts"].append(int(values.get("copy_count", 0)))
        for fixture in data.get("fixtures", []):
            name = str(fixture.get("fixture", ""))
            fixtures[name] += 1
            fixture_buckets[name].append(str(fixture.get("bucket", ">120s")))
        for boundary in data.get("boundaries", []):
            boundaries.append(boundary)
            boundary_node = str(boundary.get("nodeid", ""))
            if boundary_node.startswith("tests/"):
                boundary_node_files.add(_node_file(boundary_node))

    merged: dict[str, Any] = {
        "nodes": {},
        "fixtures": [],
        "representative_commands": {},
        "boundary_files": sorted(boundary_node_files),
    }
    for node_id, entry in sorted(nodes.items()):
        merged["nodes"][node_id] = {
            "duration_bucket": _median_bucket(entry["bucket_labels"]),
            "subprocess": _median(entry["subprocess_counts"]),
            "copy_bytes": _median(entry["copy_volume"]),
            "copy_count": _median(entry["copy_counts"]),
        }
    for name, count in fixtures.most_common():
        merged["fixtures"].append(
            {"fixture": name, "occurrences": count, "duration_bucket": _median_bucket(fixture_buckets[name])}
        )
    by_kind: dict[str, Counter[str]] = defaultdict(Counter)
    for boundary in boundaries:
        by_kind[str(boundary.get("kind", ""))][_normalize_detail(str(boundary.get("detail", "")))] += 1
    for kind, counter in sorted(by_kind.items()):
        merged["representative_commands"][kind] = [
            {"detail": detail, "count": count} for detail, count in counter.most_common(10)
        ]
    return merged


def runtime_runs(runs: int, work_dir: Path) -> dict[str, Any]:
    lane = {"args": ["-m", "not fixtures and not benchmark and not benchmark_slow"]}
    run_files: list[Path] = []
    wall_buckets: list[str] = []
    collection_buckets: list[str] = []
    for index in range(runs):
        out = work_dir / f"recorder_run{index}.json"
        started = time.monotonic()
        collect_out = work_dir / f"collect_run{index}.json"
        collect_lane(lane, str(collect_out))
        collection_buckets.append(_bucket(time.monotonic() - started))
        started = time.monotonic()
        returncode, output = _run_pytest(
            [*lane["args"], "-q"], str(out), timeout_seconds=3600
        )
        wall_buckets.append(_bucket(time.monotonic() - started))
        if returncode != 0:
            raise RuntimeError(f"baseline runtime run {index} failed:\n{output[-3000:]}")
        run_files.append(out)
    merged = _merge_recorder(run_files)
    merged["runs"] = runs
    merged["wall_duration_buckets"] = wall_buckets
    merged["collection_duration_buckets"] = collection_buckets
    return merged


def validate_exceptions(exceptions: dict[str, Any], collected: set[str]) -> list[str]:
    errors: list[str] = []

    def referenced(node_id: Any) -> bool:
        return (
            isinstance(node_id, str)
            and node_id != ""
            and (node_id in collected or any(node.startswith(node_id) for node in collected))
        )

    for entry in exceptions.get("excluded", []):
        node_id = entry.get("node_id")
        if not referenced(node_id):
            errors.append(f"excluded node references nothing collected: {node_id!r}")
    for node_id in exceptions.get("classification_overrides", {}):
        if not referenced(node_id):
            errors.append(f"classification override references nothing collected: {node_id!r}")
    return errors


def structural_payload(report: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in report.items() if key != "runtime"}


def check_report(report_path: Path, root: Path, lanes_path: Path, exceptions_path: Path) -> int:
    if not report_path.exists():
        print(f"missing committed report: {report_path}", file=sys.stderr)
        return 1
    committed = _load_json(report_path)
    if committed.get("schema_version") != 1:
        print("committed report has unsupported schema_version", file=sys.stderr)
        return 1
    try:
        regenerated = build_structural(root, lanes_path, exceptions_path)
    except RuntimeError as exc:
        print(f"regeneration failed: {exc}", file=sys.stderr)
        return 1
    collected = {row["node_id"] for row in regenerated["inventory"]}
    exceptions = _load_json(exceptions_path)
    errors = validate_exceptions(exceptions, collected)
    for error in errors:
        print(f"exception error: {error}", file=sys.stderr)
    committed_payload = structural_payload(committed)
    regenerated_payload = structural_payload(regenerated)
    if _canonical_json(committed_payload) != _canonical_json(regenerated_payload):
        print("structural drift detected between committed and regenerated baseline", file=sys.stderr)
        for key in sorted(set(committed_payload) | set(regenerated_payload)):
            if committed_payload.get(key) != regenerated_payload.get(key):
                print(f"  differing top-level section: {key}", file=sys.stderr)
        return 1
    if errors:
        return 1
    print("structural baseline and exceptions are consistent")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collect-only", action="store_true", help="build structural sections only")
    parser.add_argument("--runs", type=int, default=1, help="runtime evidence runs (default 1, max 3)")
    parser.add_argument("--check", action="store_true", help="verify committed report against regeneration")
    parser.add_argument("--report-path", type=Path, default=REPORT_PATH, help="override committed report path")
    parser.add_argument("--lanes-path", type=Path, default=LANES_PATH, help="override lane manifest path")
    parser.add_argument("--exceptions-path", type=Path, default=EXCEPTIONS_PATH, help="override exceptions path")
    parser.add_argument("--work-dir", type=Path, default=None, help="scratch directory for recorder outputs")
    args = parser.parse_args(argv)

    if args.check:
        return check_report(args.report_path, ROOT, args.lanes_path, args.exceptions_path)

    report = build_structural(ROOT, args.lanes_path, args.exceptions_path)
    collected = {row["node_id"] for row in report["inventory"]}
    exceptions = _load_json(args.exceptions_path)
    errors = validate_exceptions(exceptions, collected)
    if errors:
        for error in errors:
            print(f"exception error: {error}", file=sys.stderr)
        return 1

    if not args.collect_only:
        runs = max(1, min(args.runs, 3))
        work_dir = args.work_dir or Path(tempfile.mkdtemp(prefix="test-baseline-"))
        work_dir.mkdir(parents=True, exist_ok=True)
        report["runtime"] = runtime_runs(runs, work_dir)
        unexercised: dict[str, Any] = {}
        boundary_files = set(report["runtime"]["boundary_files"])
        for kind, files in report["static"].items():
            missing = [file for file in files if file not in boundary_files]
            if missing:
                unexercised[kind] = missing
        report["runtime"]["static_unexercised"] = unexercised

    payload = _canonical_json(report)
    args.report_path.write_text(payload, encoding="utf-8")
    print(f"wrote {args.report_path} ({len(payload)} bytes, {len(report['inventory'])} inventory rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
