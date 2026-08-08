from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "validation"))

import build_test_baseline as baseline  # noqa: E402
from build_test_baseline import (  # noqa: E402
    _classify,
    _derive_layer,
    _extract_failure_excerpt,
    _failure_locality,
    _find_failure_summary,
    _inspect_node_ast,
    _merge_recorder,
    _normalize_detail,
    _owner_of,
    validate_exceptions,
    validate_failure_samples,
    validate_runtime_evidence,
)
from test_baseline_failure_mutations import (  # noqa: E402
    apply_failure_sample_text_mutation,
    validate_failure_sample_mutation,
)
from test_baseline_utils import bucket_seconds  # noqa: E402

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
    assert bucket_seconds(0.0) == "0s"
    assert bucket_seconds(0.04) == "0s"
    assert bucket_seconds(0.05) == "0.05s"
    assert bucket_seconds(2.5) == "2s"
    assert bucket_seconds(500.0) == ">120s"


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
        == "primary-proof"
    )


def test_owner_derivation_rules() -> None:
    assert _owner_of("tests/skills/plan-change/test_v6_intake.py::test_a") == "skills/engineering/plan-change"
    assert _owner_of("tests/repository/test_x.py::test_a") == "repository"
    assert _owner_of("tests/shared/test_x.py::test_a") == "shared-runtime"
    assert _owner_of("tests/skill_protocol/test_x.py::test_a") == "shared-protocol"
    assert _owner_of("tests/integration/test_x.py::test_a") == "installed-execution"
    assert _owner_of("tests/benchmarks/test_x.py::test_a") == "benchmark-fixture"
    assert _owner_of("tests/classification/test_x.py::test_a") == "classification"
    assert (
        _owner_of("benchmarks/repos/schema-migration-service/tests/test_x.py::test_a")
        == "external-fixture"
    )
    # owner_overrides exception support
    override_exc = {"owner_overrides": {"tests/repository/test_x.py": "skills/engineering/custom"}}
    assert _owner_of("tests/repository/test_x.py::test_a", override_exc) == "skills/engineering/custom"


def test_failure_locality_rules() -> None:
    assert _failure_locality("tests/skills/plan-change/test_x.py::test_a", "skills/engineering/plan-change") == "direct"
    assert _failure_locality("tests/integration/test_x.py::test_a", "installed-execution") == "broad"
    assert _failure_locality("tests/benchmarks/test_x.py::test_a", "benchmark-fixture") == "broad"
    assert _failure_locality("tests/shared/test_x.py::test_a", "shared-runtime") == "broad"
    assert _failure_locality("tests/repository/test_x.py::test_a", "repository") == "path-derived"
    assert _failure_locality("tests/classification/test_x.py::test_a", "classification") == "path-derived"


def test_validate_exceptions_rejects_unreferenced_nodes() -> None:
    errors = validate_exceptions(
        {"excluded": [{"node_id": "tests/nonexistent.py::test_x", "reason": "gone"}],
         "owner_overrides": {"tests/nonexistent.py::test_y": "repository"},
         "ownership_notes": {"unknown.lane": {"boundary_justified": "nope"}}},
        {"tests/real.py::test_z"},
        {"quality.full"},
    )
    assert len(errors) == 3


def test_validate_exceptions_accepts_exact_and_prefix_nodes() -> None:
    errors = validate_exceptions(
        {"excluded": [{"node_id": "tests/real.py::test_z", "reason": "exact"}],
         "owner_overrides": {"tests/real.py": "repository"},
         "ownership_notes": {"quality.full": {"boundary_justified": "required"}}},
        {"tests/real.py::test_z"},
        {"quality.full"},
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
            import os
            import shutil
            import subprocess

            def test_a(tmp_path):
                subprocess.run(["git", "status"], check=False)
                subprocess.run(["pip", "install", "x"], check=False)
                shutil.copytree(tmp_path, tmp_path / "copy")
                os.environ["OPENAI_API_KEY"]
            """
        ),
        encoding="utf-8",
    )
    static = baseline.static_scan(tmp_path)
    kinds = {kind for kind, files in static.items() if files}
    assert "run" in kinds
    assert "copytree" in kinds
    assert "installer" in kinds
    assert "external-tool" in kinds
    assert "credential" in kinds


def test_inspect_node_ast_classifies_boundaries(tmp_path: Path) -> None:
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_demo.py").write_text(
        textwrap.dedent(
            """
            import os
            import subprocess
            import sys

            def test_boundary_heavy(tmp_path):
                subprocess.run(["pip", "install", "x"], check=False)
                subprocess.run(["git", "status"], check=False)
                subprocess.run(["curl", "https://example.test"], check=False)
                subprocess.run(["python", "-m", "pip", "install", "y"], check=False)
                subprocess.run(["python", "-c", "print(1)"], check=False)
                subprocess.run([sys.executable, "-S", "script.py"], check=False)
                os.environ["OPENAI_API_KEY"]

            def test_plain(tmp_path):
                assert True
            """
        ),
        encoding="utf-8",
    )
    heavy, _ = _inspect_node_ast(tmp_path, "tests/test_demo.py", "tests/test_demo.py::test_boundary_heavy")
    plain, _ = _inspect_node_ast(tmp_path, "tests/test_demo.py", "tests/test_demo.py::test_plain")
    assert set(heavy) == {"subprocess", "installer", "external-tool", "network", "credential"}
    assert plain == []


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

            def test_copy2_records_bytes(tmp_path: Path) -> None:
                source = tmp_path / "source2.txt"
                source.write_text("hello2", encoding="utf-8")
                shutil.copy2(source, tmp_path / "target2.txt")

            def test_copy_records_bytes(tmp_path: Path) -> None:
                source = tmp_path / "source3.txt"
                source.write_text("hello3", encoding="utf-8")
                shutil.copy(source, tmp_path / "target3.txt")
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
    assert "4 passed" in output
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
    assert data["nodes"][copy_node]["copy_bytes"] == 5
    for node in data["nodes"]:
        if node.endswith("::test_copy2_records_bytes"):
            assert data["nodes"][node]["copy_bytes"] == 6
        if node.endswith("::test_copy_records_bytes"):
            assert data["nodes"][node]["copy_bytes"] == 6


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


def test_validate_failure_samples_accepts_and_rejects() -> None:
    collected = {"tests/real.py::test_z"}
    good = {"schema_version": 1, "samples": [
        {"node_id": "tests/real.py::test_z",
         "mutation": {"type": "json-set", "path": "benchmarks/reports/plan-change-v7.json",
                      "target": ["schema_version"], "value": 4}},
    ]}
    assert validate_failure_samples(good, collected, REPO_ROOT) == []
    bad = {"schema_version": 1, "samples": [
        {"node_id": "tests/missing.py::test_a",
         "mutation": {"type": "json-set", "path": "benchmarks/reports/plan-change-v7.json",
                      "target": ["schema_version"], "value": 4}},
        {"node_id": "tests/real.py::test_z",
         "mutation": {"type": "unknown", "path": "benchmarks/reports/does-not-exist.json"}},
    ]}
    errors = validate_failure_samples(bad, collected, REPO_ROOT)
    assert len(errors) == 2
    schema_errors = validate_failure_samples({"schema_version": 9, "samples": []}, collected, REPO_ROOT)
    assert len(schema_errors) == 1


def _mutation_fixture(tmp_path: Path) -> tuple[str, str]:
    document = {"config": {"value": 1, "drop": "x"}, "items": ["a", "b"]}
    json_path = tmp_path / "data.json"
    text_path = tmp_path / "data.txt"
    json_path.write_text(json.dumps(document), encoding="utf-8")
    text_path.write_text("alpha beta alpha\n", encoding="utf-8")
    source = tmp_path / "src"
    (source / "nested").mkdir(parents=True)
    (source / "nested" / "present.txt").write_text("fixture\n", encoding="utf-8")
    return json_path.name, text_path.name


def test_failure_sample_mutations_accept_valid_cases(tmp_path: Path) -> None:
    json_name, text_name = _mutation_fixture(tmp_path)
    original = (tmp_path / json_name).read_text(encoding="utf-8")

    updated = json.loads(
        apply_failure_sample_text_mutation(
            original,
            {"type": "json-set", "target": ["config", "value"], "value": 2},
        )
    )
    assert updated["config"]["value"] == 2
    validate_failure_sample_mutation(
        tmp_path,
        {"type": "json-set", "path": json_name, "target": ["config", "value"], "value": 2},
    )
    created = json.loads(
        apply_failure_sample_text_mutation(
            original,
            {"type": "json-set", "target": ["config", "new_key"], "value": True},
        )
    )
    assert created["config"]["new_key"] is True
    replaced_item = json.loads(
        apply_failure_sample_text_mutation(
            original,
            {"type": "json-set", "target": ["items", 1], "value": "changed"},
        )
    )
    assert replaced_item["items"] == ["a", "changed"]
    removed_key = json.loads(
        apply_failure_sample_text_mutation(
            original, {"type": "json-remove", "target": ["config", "drop"]}
        )
    )
    assert "drop" not in removed_key["config"]
    removed_item = json.loads(
        apply_failure_sample_text_mutation(
            original, {"type": "json-remove", "target": ["items", 0]}
        )
    )
    assert removed_item["items"] == ["b"]
    validate_failure_sample_mutation(
        tmp_path,
        {"type": "json-remove", "path": json_name, "target": ["config", "drop"]},
    )
    assert apply_failure_sample_text_mutation(
        (tmp_path / text_name).read_text(encoding="utf-8"),
        {"type": "replace-string", "old": "beta", "new": "gamma"},
    ) == "alpha gamma alpha\n"
    validate_failure_sample_mutation(
        tmp_path,
        {"type": "replace-string", "path": text_name, "old": "beta", "new": "gamma"},
    )
    validate_failure_sample_mutation(
        tmp_path,
        {"type": "file-delete", "path": "src", "delete": "nested/present.txt"},
    )


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ({"type": "json-set", "path": "data.json", "target": ["missing", "value"], "value": 2}, "parent"),
        ({"type": "json-set", "path": "data.json", "target": ["items", 2], "value": "x"}, "out of range"),
        ({"type": "json-set", "path": "data.json", "target": ["items", True], "value": "x"}, "integer"),
        ({"type": "json-set", "path": "data.json", "target": ["config", "value", "nested"], "value": 2}, "non-container"),
        ({"type": "json-set", "path": "data.json", "target": ["config", "value"], "value": 1}, "would not change"),
        ({"type": "json-set", "path": "data.json", "target": ["items", 0], "value": "a"}, "would not change"),
        ({"type": "json-remove", "path": "data.json", "target": ["config", "missing"]}, "does not exist"),
        ({"type": "json-remove", "path": "data.json", "target": ["items", -1]}, "out of range"),
        ({"type": "json-remove", "path": "data.json", "target": ["items", "0"]}, "integer"),
        ({"type": "json-remove", "path": "data.json", "target": ["items", 2]}, "out of range"),
        ({"type": "json-remove", "path": "data.json", "target": ["items"], "index": 0}, "final key/index"),
        ({"type": "replace-string", "path": "data.txt", "old": "", "new": "x"}, "non-empty"),
        ({"type": "replace-string", "path": "data.txt", "old": "x", "new": ""}, "non-empty"),
        ({"type": "replace-string", "path": "data.txt", "old": "beta", "new": "beta"}, "differ"),
        ({"type": "replace-string", "path": "data.txt", "old": "missing", "new": "x"}, "exactly once"),
        ({"type": "replace-string", "path": "data.txt", "old": "alpha", "new": "x"}, "exactly once"),
        ({"type": "file-delete", "path": "src", "delete": "missing.txt"}, "does not exist"),
        ({"type": "file-delete", "path": "src", "delete": "nested"}, "does not exist as a file"),
        ({"type": "file-delete", "path": "src", "delete": "../data.json"}, "inside"),
    ],
)
def test_failure_sample_mutations_reject_invalid_cases(
    tmp_path: Path, mutation: dict[str, object], expected: str
) -> None:
    _mutation_fixture(tmp_path)
    with pytest.raises(ValueError, match=expected):
        validate_failure_sample_mutation(tmp_path, mutation)


def test_invalid_failure_sample_manifest_cannot_launch_pytest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _mutation_fixture(tmp_path)
    manifest_path = tmp_path / "samples.json"
    def fail_if_pytest_starts(*args: object, **kwargs: object) -> None:
        raise AssertionError("pytest subprocess was launched")

    monkeypatch.setattr(baseline.subprocess, "run", fail_if_pytest_starts)
    valid_sample: dict[str, Any] = {
        "node_id": "tests/real.py::test_z",
        "mutation": {
            "type": "replace-string",
            "path": "data.txt",
            "old": "alpha",
            "new": "gamma",
        },
    }
    cases = [
        ({"schema_version": 9, "samples": [valid_sample]}, {"tests/real.py::test_z"}),
        ({"schema_version": 1, "samples": [{**valid_sample, "node_id": "tests/missing.py::test_z"}]}, {"tests/real.py::test_z"}),
        (
            {
                "schema_version": 1,
                "samples": [
                    {
                        **valid_sample,
                        "mutation": {**valid_sample["mutation"], "old": "missing"},
                    }
                ],
            },
            {"tests/real.py::test_z"},
        ),
    ]
    for manifest, collected in cases:
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with pytest.raises(RuntimeError, match="before pytest"):
            baseline.run_failure_samples(tmp_path, manifest_path, collected)


def test_committed_failure_sample_manifest_is_applicable() -> None:
    manifest = json.loads(
        (REPO_ROOT / "tools" / "validation" / "test-baseline-failure-samples.json").read_text(
            encoding="utf-8"
        )
    )
    report = json.loads((REPO_ROOT / "benchmarks" / "reports" / "test-baseline.json").read_text(encoding="utf-8"))
    collected = {row["node_id"] for row in report["inventory"]}
    assert validate_failure_samples(manifest, collected, REPO_ROOT) == []


def test_runtime_evidence_contract_accepts_two_run_report() -> None:
    valid = {
        "runtime": {
            "runs": 2,
            "wall_duration_buckets": ["1s", "2s"],
            "collection_duration_buckets": ["0.1s", "0.1s"],
            "nodes": {"test": {}},
            "fixtures": [{"fixture": "tmp_path"}],
            "boundary_files": ["tests/test.py"],
            "lane_executions": {"quality.full": {}},
        }
    }
    assert validate_runtime_evidence(valid) == []
    assert validate_runtime_evidence({"runtime": {"runs": 1}})


def test_failure_diagnostic_parsing() -> None:
    node_id = (
        "tests/skills/plan-change/test_benchmark_report.py::"
        "test_committed_plan_change_benchmark_has_comparable_machine_phases_only"
    )
    output = textwrap.dedent(
        f"""\
        _________________ {node_id.split("::")[-1]} _________________
        tests/skills/plan-change/test_benchmark_report.py:15: in {node_id.split("::")[-1]}
            _assert_contract(json.loads(REPORT.read_text(encoding="utf-8")))
        tests/skills/plan-change/test_benchmark_report.py:16: in _assert_contract
        >   assert report["schema_version"] == 3
        E   AssertionError: assert 4 == 3
        =========================== short test summary info ===========================
        FAILED {node_id} - AssertionError: assert 4 == 3
        """
    )
    assert _find_failure_summary(output, node_id) == f"FAILED {node_id} - AssertionError: assert 4 == 3"
    excerpt = _extract_failure_excerpt(output, node_id)
    assert "assert report[\"schema_version\"] == 3" in excerpt
    assert "AssertionError: assert 4 == 3" in excerpt
    assert "short test summary info" not in excerpt


def _write_failure_sample_suite(tmp_path: Path) -> None:
    (tmp_path / "data.json").write_text(
        '{"schema_version": 3, "name": "x"}', encoding="utf-8"
    )
    (tmp_path / "remove.json").write_text('{"items": ["remove", "keep"]}', encoding="utf-8")
    source = tmp_path / "src"
    (source / "scripts").mkdir(parents=True)
    (source / "scripts" / "seal.py").write_text("print('seal')\n", encoding="utf-8")
    (source / "data.txt").write_text("not fixtures and not benchmark and not benchmark_slow\n", encoding="utf-8")
    (tmp_path / "test_sample_suite.py").write_text(
        textwrap.dedent(
            """
            import json
            import shutil
            from pathlib import Path

            DATA = Path(__file__).with_name("data.json")
            REMOVE = Path(__file__).with_name("remove.json")
            SRC = Path(__file__).with_name("src")
            TEXT = Path(__file__).with_name("src") / "data.txt"

            def test_json_schema_version():
                report = json.loads(DATA.read_text(encoding="utf-8"))
                assert report["schema_version"] == 3

            def test_json_remove_item():
                report = json.loads(REMOVE.read_text(encoding="utf-8"))
                assert report["items"] == ["remove", "keep"]

            def test_copied_tree_keeps_sealer(tmp_path: Path):
                installed = tmp_path / "installed"
                shutil.copytree(SRC, installed)
                assert (installed / "scripts" / "seal.py").exists()

            def test_workflow_profile_preserved():
                assert "not fixtures and not benchmark and not benchmark_slow" in TEXT.read_text(encoding="utf-8")
            """
        ),
        encoding="utf-8",
    )


def _run_sample_pytest(tmp_path: Path, suite_path: Path, manifest: dict) -> tuple[int, str]:
    manifest_path = tmp_path / "samples.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return baseline._run_pytest(
        [str(suite_path), "-p", "test_baseline_failure_samples", "--color=no", "-q"],
        None,
        extra_env={
            "TEST_BASELINE_SAMPLES_PATH": str(manifest_path),
            "TEST_BASELINE_SAMPLES_ROOT": str(tmp_path),
        },
    )


def test_failure_sample_interceptions_are_scoped_and_leave_files_untouched(tmp_path: Path) -> None:
    _write_failure_sample_suite(tmp_path)
    manifest = {
        "schema_version": 1,
        "samples": [
            {"node_id": "test_sample_suite.py::test_json_schema_version",
             "mutation": {"type": "json-set", "path": "data.json",
                          "target": ["schema_version"], "value": 4}},
            {"node_id": "test_sample_suite.py::test_json_remove_item",
             "mutation": {"type": "json-remove", "path": "remove.json",
                          "target": ["items", 0]}},
            {"node_id": "test_sample_suite.py::test_copied_tree_keeps_sealer",
             "mutation": {"type": "file-delete", "path": "src", "delete": "scripts/seal.py"}},
            {"node_id": "test_sample_suite.py::test_workflow_profile_preserved",
             "mutation": {"type": "replace-string", "path": "src/data.txt",
                          "old": "not fixtures and not benchmark and not benchmark_slow",
                          "new": "not fixtures and not benchmark"}},
        ],
    }
    returncode, output = _run_sample_pytest(tmp_path, tmp_path / "test_sample_suite.py", manifest)
    assert returncode != 0
    assert "4 failed" in output
    assert "assert 4 == 3" in output
    assert "AssertionError: assert False" in output
    assert "FAILED" in output
    assert json.loads((tmp_path / "data.json").read_text(encoding="utf-8"))["schema_version"] == 3
    assert (tmp_path / "src" / "scripts" / "seal.py").exists()
    assert "not fixtures and not benchmark and not benchmark_slow" in (tmp_path / "src" / "data.txt").read_text(encoding="utf-8")


def test_reduced_baseline_is_deterministic(tmp_path: Path) -> None:
    manifest_path = tmp_path / "lanes.json"
    manifest_path.write_text(json.dumps(REDUCED_MANIFEST), encoding="utf-8")
    first = baseline.build_structural(
        REPO_ROOT, manifest_path, EXCEPTIONS_PATH, require_sample_nodes=False
    )
    second = baseline.build_structural(
        REPO_ROOT, manifest_path, EXCEPTIONS_PATH, require_sample_nodes=False
    )
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
        if row["is_duplicate_execution"] and row["domain"] == "map-codebase"
    )
    assert "quality.full" in duplicate_row["lanes"]
    assert duplicate_row["owner"] == "skills/engineering/map-codebase"
    assert first["schema_version"] == 2
    assert first["failure_locality"]["evidence"] == "observed-sample"
    assert set(first["failure_locality"]["distribution"]) <= {"direct", "path-derived", "broad"}
    assert all(len(samples) <= 5 for samples in first["failure_locality"]["representative"].values())
    assert len(first["failure_locality"]["sample"]) == 3
    assert all(sample["diagnostic"] for sample in first["failure_locality"]["sample"])
    assert all(sample["mutation"] for sample in first["failure_locality"]["sample"])
    assert {sample["locality"] for sample in first["failure_locality"]["sample"]} == {
        "direct",
        "path-derived",
        "broad",
    }
    full_lane = first["ownership"]["lanes"]["quality.full"]
    assert full_lane["boundary_justified"] is True
    assert full_lane["unresolved"] is False
    assert "overlaps" in full_lane
    map_owner = first["ownership"]["owners"]["skills/engineering/map-codebase"]
    assert map_owner["owning_surface"] == ["skills/engineering/map-codebase/**"]
    assert map_owner["node_count"] > 100
