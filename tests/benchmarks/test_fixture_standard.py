from __future__ import annotations

import copy
import hashlib
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MAP_SCRIPTS = ROOT / "skills" / "engineering" / "map-codebase" / "scripts"

import tools.benchmarks.fixtures as fixture_tools
from tools.benchmarks.catalog import AUDIT_PATH, render_audit
from tools.benchmarks.fixtures import (
    BenchmarkError,
    FixtureTree,
    inspect_fixture_tree,
    load_manifests,
    materialize_repository,
    repository_digest,
    validate_manifest,
    verify_fixture_tree,
)

pytestmark = pytest.mark.fixtures


def test_committed_manifests_and_evidence_hashes_validate() -> None:
    manifests = load_manifests()
    assert {manifest["fixture_id"] for manifest in manifests} == {
        "flag-control-plane",
        "subscription-platform",
    }
    for manifest in manifests:
        repository = ROOT / "benchmarks" / "repos" / manifest["repository"]["path"]
        tree = FixtureTree.from_mapping(manifest["repository"])
        verify_fixture_tree(repository, tree)
        assert repository_digest(repository) == tree.sha256


def test_fixture_tree_contract_rejects_malformed_inventories(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_bytes(b"alpha\n")
    (tmp_path / "b.txt").write_bytes(b"beta\n")
    mapping = inspect_fixture_tree(tmp_path).to_mapping()

    unsorted = copy.deepcopy(mapping)
    unsorted["files"].reverse()
    with pytest.raises(BenchmarkError, match="must be sorted"):
        FixtureTree.from_mapping(unsorted)

    duplicate = copy.deepcopy(mapping)
    duplicate["files"][1] = copy.deepcopy(duplicate["files"][0])
    with pytest.raises(BenchmarkError, match="duplicate paths"):
        FixtureTree.from_mapping(duplicate)

    traversal = copy.deepcopy(mapping)
    traversal["files"][0]["path"] = "../answer.txt"
    with pytest.raises(BenchmarkError, match="contained relative path"):
        FixtureTree.from_mapping(traversal)

    stale = copy.deepcopy(mapping)
    stale["sha256"] = "0" * 64
    with pytest.raises(BenchmarkError, match="stale aggregate tree hash"):
        FixtureTree.from_mapping(stale)


def test_fixture_tree_ignores_runtime_caches_but_fails_on_source_drift(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    declared = source / "module.py"
    declared.write_bytes(b"VALUE = 1\n")
    (source / "keep.txt").write_bytes(b"keep\n")
    expected = inspect_fixture_tree(source)

    cache = source / ".ruff_cache" / "state"
    cache.parent.mkdir()
    cache.write_bytes(b"machine-local")
    verify_fixture_tree(source, expected)

    unexpected = source / "answer.json"
    unexpected.write_bytes(b"{}\n")
    with pytest.raises(BenchmarkError, match="unexpected source path"):
        verify_fixture_tree(source, expected)
    unexpected.unlink()

    declared.write_bytes(b"VALUE = 1\r\n")
    with pytest.raises(BenchmarkError, match="content hash mismatch"):
        verify_fixture_tree(source, expected)
    declared.write_bytes(b"VALUE = 1\n")

    declared.unlink()
    with pytest.raises(BenchmarkError, match="missing declared path"):
        verify_fixture_tree(source, expected)


def test_materialization_copies_only_declared_inventory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repositories = tmp_path / "repos"
    source = repositories / "fixture"
    source.mkdir(parents=True)
    (source / "module.py").write_bytes(b"VALUE = 1\n")
    tree = inspect_fixture_tree(source)
    cache = source / ".pytest_cache" / "state"
    cache.parent.mkdir()
    cache.write_bytes(b"machine-local")
    manifest = {
        "fixture_id": "fixture",
        "repository": {"path": "fixture", **tree.to_mapping()},
    }
    monkeypatch.setattr(fixture_tools, "REPOSITORY_ROOT", repositories)

    with materialize_repository(manifest) as materialized:
        assert (materialized / "module.py").read_bytes() == b"VALUE = 1\n"
        assert not (materialized / ".pytest_cache").exists()


def test_manifest_rejects_stale_owner_evidence_and_prompt_leakage() -> None:
    manifest = load_manifests()[0]
    stale = copy.deepcopy(manifest)
    stale["tasks"][0]["expected"]["primary_owners"][0]["sha256"] = "0" * 64
    with pytest.raises(BenchmarkError, match="stale evidence"):
        validate_manifest(stale)

    leaked = copy.deepcopy(manifest)
    leaked["tasks"][0]["prompt"] += f" {manifest['fixture_id']}"
    with pytest.raises(BenchmarkError, match="leaks fixture id"):
        validate_manifest(leaked)

    duplicate = copy.deepcopy(manifest)
    duplicate["tasks"][1]["id"] = duplicate["tasks"][0]["id"]
    with pytest.raises(BenchmarkError, match="duplicate task id"):
        validate_manifest(duplicate)

    unknown_oracle = copy.deepcopy(manifest)
    unknown_oracle["tasks"][0]["verification"]["oracles"][0]["kind"] = "model-judge"
    with pytest.raises(BenchmarkError, match="unsupported oracle"):
        validate_manifest(unknown_oracle)


def test_manifest_rejects_traversal_and_shell_control_tokens() -> None:
    manifest = load_manifests()[0]
    traversal = copy.deepcopy(manifest)
    traversal["repository"]["path"] = "../flag-control-plane"
    with pytest.raises(BenchmarkError, match="contained relative path"):
        validate_manifest(traversal)

    injected = copy.deepcopy(manifest)
    injected["tasks"][0]["verification"]["commands"] = [["{python}", "-m", "pytest", "&&"]]
    with pytest.raises(BenchmarkError, match="shell control token"):
        validate_manifest(injected)


def test_materialization_is_temporary_and_does_not_embed_ground_truth() -> None:
    manifest = load_manifests()[0]
    with materialize_repository(manifest) as repository:
        temporary_root = repository.parent
        assert repository.is_dir()
        assert not (repository / "benchmarks").exists()
        assert not any(path.name.endswith("answer.json") for path in repository.rglob("*"))
    assert not temporary_root.exists()


def test_generator_and_fixture_catalog_have_no_drift() -> None:
    generated = subprocess.run(
        [
            sys.executable,
            str(ROOT / "benchmarks" / "generators" / "generate.py"),
            "--check",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert generated.returncode == 0, generated.stdout + generated.stderr
    rendered = render_audit()
    assert AUDIT_PATH.read_text(encoding="utf-8") == rendered
    assert "decision-quality-hidden-consumer" not in rendered
    assert "decision-quality-null-guard" not in rendered


def test_external_symlink_escape_is_rejected(tmp_path: Path) -> None:
    manifest = copy.deepcopy(load_manifests()[0])
    repository = ROOT / "benchmarks" / "repos" / manifest["repository"]["path"]
    link = repository / "escape-link"
    outside = tmp_path / "outside.txt"
    outside.write_text("outside\n", encoding="utf-8")
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation is unavailable on this Windows host")
    try:
        with pytest.raises(BenchmarkError, match="may not contain symlinks"):
            validate_manifest(manifest)
    finally:
        link.unlink(missing_ok=True)


def test_generated_repositories_are_domain_shaped_not_numbered_clones() -> None:
    for repository in sorted((ROOT / "benchmarks" / "repos").iterdir()):
        files = [path for path in repository.rglob("*") if path.is_file()]
        numbered = [
            path
            for path in files
            if re.search(r"(?:^|[_-])\d{2,}(?:[_.-]|$)", path.name)
        ]
        assert len(numbered) / len(files) < 0.10
        content_counts = Counter(
            hashlib.sha256(path.read_bytes()).hexdigest()
            for path in files
            if path.name != "__init__.py"
        )
        assert max(content_counts.values()) <= 5
        assert not any(re.search(r"(?:component|module)_\d+", path.stem) for path in files)


def test_answers_do_not_leak_into_installed_resolver() -> None:
    production = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in (MAP_SCRIPTS).rglob("*.py")
    )
    for manifest in load_manifests():
        assert manifest["fixture_id"] not in production
        for task in manifest["tasks"]:
            for owner in task["expected"]["primary_owners"]:
                assert owner["path"] not in production


def test_ci_profiles_keep_fixture_runtime_and_benchmark_evidence_separate() -> None:
    quality = (ROOT / ".github" / "workflows" / "quality.yml").read_text(encoding="utf-8")
    full = (ROOT / ".github" / "workflows" / "benchmarks.yml").read_text(encoding="utf-8")

    assert 'os: [ubuntu-latest, windows-latest]' in quality
    assert 'pytest -m fixtures -q' in quality
    assert 'not fixtures and not benchmark and not benchmark_slow' in quality
    assert 'benchmark and not benchmark_slow' in quality
    assert 'timeout-minutes: 10' in quality
    assert 'pytest -m benchmark_slow -q' in full
    assert 'pytest -m benchmark -q' not in full
