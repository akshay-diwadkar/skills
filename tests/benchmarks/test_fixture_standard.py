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

from tools.benchmarks.catalog import AUDIT_PATH, render_audit
from tools.benchmarks.fixtures import (
    BenchmarkError,
    load_manifests,
    materialize_repository,
    repository_digest,
    validate_manifest,
)

pytestmark = pytest.mark.fixtures


def test_committed_manifests_and_evidence_hashes_validate() -> None:
    manifests = load_manifests()
    assert {manifest["fixture_id"] for manifest in manifests} == {
        "flag-control-plane",
        "subscription-platform",
    }
    assert all(repository_digest(ROOT / "benchmarks" / "repos" / manifest["repository"]["path"]) == manifest["repository"]["sha256"] for manifest in manifests)


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
    assert AUDIT_PATH.read_text(encoding="utf-8") == render_audit()


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
        manifest["repository"]["sha256"] = repository_digest(repository)
        with pytest.raises(BenchmarkError, match="symlink escapes"):
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
