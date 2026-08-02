"""Regression coverage for index-first discovery and deterministic evidence reuse."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "engineering" / "map-codebase" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from build_knowledge import build_knowledge
from knowledge.discovery import git_file_states, git_tracked_paths
from knowledge.relationships import build_relationship_graph, resolve_import_to_path
from resolve_task import _scoped_source_terms


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def test_typescript_emitted_js_import_resolves_to_source_owner() -> None:
    indexed = {
        "plugins/app.ts",
        "tests/app/onboard-component.test.ts",
    }

    assert resolve_import_to_path(
        "../../plugins/app.js",
        indexed,
        "tests/app/onboard-component.test.ts",
    ) == "plugins/app.ts"


def test_java_test_suffix_links_to_maintained_source() -> None:
    files = [
        {"path": "src/CatalogPolicy.java", "role": "source", "imports": []},
        {"path": "test/CatalogPolicyTest.java", "role": "test", "imports": []},
    ]

    _, _, tests = build_relationship_graph(files, [])

    assert tests == [{
        "path": "test/CatalogPolicyTest.java",
        "targets": ["src/CatalogPolicy.java"],
    }]


def test_porcelain_v2_separates_index_worktree_and_untracked(sample_repo: Path) -> None:
    tracked = sample_repo / "src" / "auth" / "service.py"
    tracked.write_text(tracked.read_text(encoding="utf-8") + "\n# staged\n", encoding="utf-8")
    _git(sample_repo, "add", "src/auth/service.py")
    tracked.write_text(tracked.read_text(encoding="utf-8") + "# worktree\n", encoding="utf-8")
    (sample_repo / "scratch.py").write_text("def local(): pass\n", encoding="utf-8")

    states = git_file_states(sample_repo)
    assert git_tracked_paths(sample_repo) is not None
    assert states["src/auth/service.py"] == {"tracked": True, "index": True, "worktree": True, "untracked": False}
    assert states["scratch.py"] == {"tracked": False, "index": False, "worktree": False, "untracked": True}


def test_porcelain_v2_uses_renamed_path_as_current_owner(sample_repo: Path) -> None:
    _git(sample_repo, "mv", "src/auth/service.py", "src/auth/identity.py")
    states = git_file_states(sample_repo)
    assert states["src/auth/identity.py"] == {"tracked": True, "index": True, "worktree": False, "untracked": False}
    assert "src/auth/service.py" not in states


def test_worker_counts_and_reused_evidence_are_byte_deterministic(sample_repo: Path) -> None:
    serial = sample_repo / ".agent" / "knowledge"
    build_knowledge(sample_repo, serial, worker_count=1)
    first_artifacts = {
        name: (serial / name).read_bytes()
        for name in ("repo-map.json", "relationships.json", "symbols.json", "symbol-index.json", "evidence-index.json")
    }
    build_knowledge(sample_repo, serial, worker_count=4)

    for name, content in first_artifacts.items():
        assert content == (serial / name).read_bytes()

    first = json.loads((serial / "evidence-index.json").read_text(encoding="utf-8"))
    build_knowledge(sample_repo, serial, worker_count=1)
    second = json.loads((serial / "evidence-index.json").read_text(encoding="utf-8"))
    assert first == second
    assert all((serial / item["shard"]).is_file() for item in second["shards"])


def test_invalid_worker_count_is_rejected(sample_repo: Path) -> None:
    with pytest.raises(ValueError, match="worker_count"):
        build_knowledge(sample_repo, sample_repo / ".agent" / "knowledge", worker_count=0)


def test_generated_source_links_are_indexed_as_relationship_evidence(tmp_path: Path) -> None:
    (tmp_path / "schemas").mkdir()
    (tmp_path / "generated").mkdir()
    (tmp_path / "schemas" / "events.json").write_text('{"type": "object"}\n', encoding="utf-8")
    (tmp_path / "generated" / "events.ts").write_text(
        "// Generated from schemas/events.json.\nexport const event = {};\n", encoding="utf-8"
    )
    output = tmp_path / ".agent" / "knowledge"
    build_knowledge(tmp_path, output)
    relationships = json.loads((output / "relationships.json").read_text(encoding="utf-8"))
    assert relationships["generated_links"] == [{
        "source": "generated/events.ts", "target": "schemas/events.json", "kind": "generated-from", "confidence": "high",
    }]


def test_scoped_ripgrep_fallback_remains_bounded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "owner.py").write_text("tenant = 'north'\n" + "ignored = 0\n" * 300, encoding="utf-8")

    def unavailable(*args: object, **kwargs: object) -> None:
        raise FileNotFoundError()

    monkeypatch.setattr("resolve_task.subprocess.run", unavailable)
    evidence = _scoped_source_terms(tmp_path, frozenset({"src/owner.py"}), {"tenant"})
    assert "tenant" in evidence["src/owner.py"]
    assert "ignored" not in evidence["src/owner.py"]
