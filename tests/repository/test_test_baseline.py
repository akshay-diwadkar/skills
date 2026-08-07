from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "validation"))

import build_test_baseline as baseline  # noqa: E402
from build_test_baseline import (  # noqa: E402
    _bucket,
    _classify,
    _derive_layer,
    _merge_recorder,
    _normalize_detail,
    validate_exceptions,
)

LANES_PATH = REPO_ROOT / "tools" / "validation" / "test-baseline-lanes.json"
EXCEPTIONS_PATH = REPO_ROOT / "tools" / "validation" / "test-baseline-exceptions.json"

REDUCED_MANIFEST = {
    "schema_version": 1,
    "lanes": [
        {"id": "quality.full", "workflow": "quality.yml", "job": "quality",
         "args": ["-m", "not fixtures and not benchmark and not benchmark_slow"],
         "matrix_cells": [], "env_gated": False},
        {"id": "quality.map-codebase-clean-install", "workflow": "quality.yml",
         "job": "map-codebase-clean-install",
         "args": ["tests/skills/map-codebase", "-m",
                  "not fixtures and not benchmark and not benchmark_slow"],
         "matrix_cells": [], "env_gated": False},
    ],
}


def test_bucket_boundaries() -> None:
    assert _bucket(0.0) == "0s"
    assert _bucket(0.04) == "0s"
    assert _bucket(0.05) == "0.05s"
    assert _bucket(2.5) == "2s"
    assert _bucket(500.0) == ">120s"


def test_derive_layer_rules() -> None:
    assert _derive_layer("tests/repository/test_x.py::test_a") == "repository-policy"
    assert _derive_layer("tests/shared/test_x.py::test_a") == "shared-runtime"
    assert _derive_layer("tests/skill_protocol/test_x.py::test_a") == "shared-protocol"
    assert _derive_layer("tests/classification/test_x.py::test_a") == "classification"
    assert _derive_layer("tests/integration/test_x.py::test_a") == "installed-execution"
    assert _derive_layer("tests/benchmarks/test_x.py::test_a") == "benchmark-fixture"
    assert _derive_layer("tests/skills/plan-change/test_x.py::test_a") == "skill-local"
    assert (
        _derive_layer(
            "tests/skills/implement-plan/evals/fixtures/legacy-tiny-plan/tests/test_x.py::test_a"
        )
        == "fixture-repository"
    )
    assert (
        _derive_layer("tests/skills/map-codebase/eval/repos/python-small/tests/test_x.py::test_a")
        == "fixture-repository"
    )


def test_classify_rules() -> None:
    assert _classify("tests/skills/plan-change/test_x.py::test_a", ["fixtures"], ["quality.full"]) == "fixture-integrity"
    assert _classify("tests/skills/plan-change/test_x.py::test_a", ["benchmark"], ["quality.full"]) == "benchmark-evidence"
    assert _classify("tests/integration/test_x.py::test_a", [], ["quality.full"]) == "compatibility-check"
    assert (
        _classify(
            "tests/skills/plan-change/evals/fixtures/tiny-test-gap/tests/test_x.py::test_a",
            [],
            ["quality.full"],
        )
        == "fixture-composition"
    )
    assert (
        _classify("tests/skills/plan-change/test_x.py::test_a", [], ["quality.full"])
        == "primary-proof"
    )
    assert (
        _classify("tests/skills/plan-change/test_x.py::test_a", [], ["quality.full", "plan-change-hardening.plan-change"])
        == "suspected-duplicate"
    )


def test_validate_exceptions_rejects_unreferenced_nodes() -> None:
    errors = validate_exceptions(
        {"excluded": [{"node_id": "tests/nonexistent.py::test_x", "reason": "gone"}],
         "classification_overrides": {"tests/nonexistent.py::test_y": "primary-proof"}},
        {"tests/real.py::test_z"},
    )
    assert len(errors) == 2


def test_validate_exceptions_accepts_exact_and_prefix_nodes() -> None:
    errors = validate_exceptions(
        {"excluded": [{"node_id": "tests/real.py::test_z", "reason": "exact"}],
         "classification_overrides": {"tests/real.py": "primary-proof"}},
        {"tests/real.py::test_z"},
    )
    assert errors == []


def test_normalize_detail_strips_machine_paths(tmp_path: Path) -> None:
    normalized = _normalize_detail(
        str(tmp_path / "repo" / "src") + " ; " + str(Path.cwd() / "tools" / "validation")
    )
    assert "%TEMP%" in normalized
    assert "tools/validation" in normalized
    assert str(tmp_path) not in normalized


def test_static_scan_detects_boundary_usage(tmp_path: Path) -> None:
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_demo.py").write_text(
        textwrap.dedent(
            """
            import shutil
            import subprocess

            def test_a(tmp_path):
                subprocess.run(["git", "status"], check=False)
                shutil.copytree(tmp_path, tmp_path / "copy")
            """
        ),
        encoding="utf-8",
    )
    static = baseline.static_scan(tmp_path)
    kinds = {kind for kind, files in static.items() if files}
    assert "run" in kinds
    assert "copytree" in kinds


def _write_instrumentation_suite(tmp_path: Path) -> None:
    (tmp_path / "test_instrumentation_demo.py").write_text(
        textwrap.dedent(
            """
            import shutil
            import subprocess
            from pathlib import Path

            def test_subprocess_boundary(tmp_path: Path) -> None:
                result = subprocess.run(
                    ["python", "-c", "print(41 + 1)"], capture_output=True, text=True, check=False
                )
                assert result.returncode == 0
                assert result.stdout.strip() == "42"

            def test_copy_boundary(tmp_path: Path) -> None:
                source = tmp_path / "source.txt"
                source.write_text("hello", encoding="utf-8")
                target = tmp_path / "target.txt"
                shutil.copyfile(source, target)
                assert target.read_text(encoding="utf-8") == "hello"
            """
        ),
        encoding="utf-8",
    )


def test_instrumentation_is_semantics_preserving_and_records(tmp_path: Path) -> None:
    _write_instrumentation_suite(tmp_path)
    recorder_out = tmp_path / "recorder.json"
    returncode, output = baseline._run_pytest(
        [str(tmp_path / "test_instrumentation_demo.py"), "-q"], str(recorder_out)
    )
    assert returncode == 0, output
    assert "2 passed" in output
    assert "failed" not in output
    assert recorder_out.exists()
    data = json.loads(recorder_out.read_text(encoding="utf-8"))
    subprocess_node = next(
        node for node in data["markers"] if node.endswith("::test_subprocess_boundary")
    )
    copy_node = next(node for node in data["nodes"] if node.endswith("::test_copy_boundary"))
    assert data["markers"][subprocess_node] == []
    assert any(
        boundary["kind"] == "subprocess" and "print(41 + 1)" in boundary["detail"]
        for boundary in data["boundaries"]
    )
    assert any(boundary["kind"] == "copy" for boundary in data["boundaries"])
    assert data["nodes"][copy_node]["copy_count"] >= 1


def test_merge_recorder_medians_across_runs(tmp_path: Path) -> None:
    (tmp_path / "run0.json").write_text(
        json.dumps(
            {
                "nodes": {
                    "tests/x.py::test_a": {"bucket": "0.5s", "subprocess": 2, "copy_bytes": 100, "copy_count": 1},
                    "tests/x.py::test_b": {"bucket": "1s", "subprocess": 0, "copy_bytes": 0, "copy_count": 0},
                },
                "fixtures": [
                    {"fixture": "tmp_path", "baseid": "", "bucket": "0.1s"},
                    {"fixture": "tmp_path", "baseid": "", "bucket": "0.5s"},
                ],
                "boundaries": [
                    {"nodeid": "tests/x.py::test_a", "kind": "subprocess", "detail": "git status", "volume": 0}
                ],
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "run1.json").write_text(
        json.dumps(
            {
                "nodes": {
                    "tests/x.py::test_a": {"bucket": "1s", "subprocess": 4, "copy_bytes": 300, "copy_count": 2},
                    "tests/x.py::test_b": {"bucket": "2s", "subprocess": 0, "copy_bytes": 0, "copy_count": 0},
                },
                "fixtures": [
                    {"fixture": "tmp_path", "baseid": "", "bucket": "0.25s"},
                    {"fixture": "tmp_path", "baseid": "", "bucket": "0.1s"},
                ],
                "boundaries": [],
            }
        ),
        encoding="utf-8",
    )
    merged = _merge_recorder([tmp_path / "run0.json", tmp_path / "run1.json"])
    assert merged["nodes"]["tests/x.py::test_a"]["subprocess"] == 2
    assert merged["nodes"]["tests/x.py::test_a"]["copy_bytes"] == 100
    assert merged["nodes"]["tests/x.py::test_a"]["duration_bucket"] == "0.5s"
    assert merged["nodes"]["tests/x.py::test_b"]["duration_bucket"] == "1s"
    assert merged["fixtures"][0]["fixture"] == "tmp_path"
    assert merged["fixtures"][0]["occurrences"] == 4
    assert merged["boundary_files"] == ["tests/x.py"]


def test_reduced_baseline_is_deterministic(tmp_path: Path) -> None:
    manifest_path = tmp_path / "lanes.json"
    manifest_path.write_text(json.dumps(REDUCED_MANIFEST), encoding="utf-8")
    first = baseline.build_structural(REPO_ROOT, manifest_path, EXCEPTIONS_PATH)
    second = baseline.build_structural(REPO_ROOT, manifest_path, EXCEPTIONS_PATH)
    assert baseline._canonical_json(first) == baseline._canonical_json(second)
    full = next(lane for lane in first["lanes"] if lane["id"] == "quality.full")
    assert full["node_count"] > 800
    map_lane = next(lane for lane in first["lanes"] if lane["id"] == "quality.map-codebase-clean-install")
    assert map_lane["node_count"] > 100
    overlap = set(full["node_ids"]) & set(map_lane["node_ids"])
    assert len(overlap) == map_lane["node_count"]
    duplicate_row = next(
        row
        for row in first["inventory"]
        if row["classification"] == "suspected-duplicate" and row["domain"] == "map-codebase"
    )
    assert "quality.full" in duplicate_row["lanes"]
