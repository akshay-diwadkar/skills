from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import pytest

from .v7_helpers import RUNTIME, make_repo, tiny_plan  # type: ignore[import-not-found]

seal_plan = RUNTIME.seal_plan


def test_sealer_never_uses_recursive_discovery(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    request = tmp_path / "request.md"
    draft = tmp_path / "draft.md"
    request.write_text("Fix absent names.\n", encoding="utf-8")
    draft.write_text(tiny_plan(), encoding="utf-8")
    monkeypatch.setattr(Path, "rglob", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("rglob forbidden")))
    original_glob = Path.glob

    def guarded_glob(self: Path, pattern: str):
        if "**" in pattern:
            raise AssertionError("recursive glob forbidden")
        return original_glob(self, pattern)

    monkeypatch.setattr(Path, "glob", guarded_glob)
    monkeypatch.setattr(os, "walk", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("walk forbidden")))
    original_run = subprocess.run

    def guarded_run(argv, *args, **kwargs):
        rendered = " ".join(str(value) for value in argv)
        assert "ls-files" not in rendered
        assert "git grep" not in rendered
        assert not rendered.startswith("rg ")
        assert "grep -r" not in rendered and "grep -R" not in rendered
        return original_run(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", guarded_run)
    result = seal_plan(repo, request, draft)
    assert result.counters["opened_paths"] == ["src/names.py"]
    assert result.counters["hash_count"] == 1


def test_repository_size_does_not_change_operations(tmp_path: Path) -> None:
    small = make_repo(tmp_path / "small")
    large = make_repo(tmp_path / "large")
    noise = large / "unrelated"
    noise.mkdir()
    noise_count = 50_000 if os.environ.get("PLAN_CHANGE_LARGE_REPO") == "1" else 5_000
    for index in range(noise_count):
        (noise / f"file_{index:05d}.txt").write_text("x", encoding="utf-8")
    request = tmp_path / "request.md"
    draft = tmp_path / "draft.md"
    request.write_text("Fix absent names.\n", encoding="utf-8")
    draft.write_text(tiny_plan(), encoding="utf-8")
    small_counts = seal_plan(small, request, draft).counters
    started = time.perf_counter()
    large_counts = seal_plan(large, request, draft).counters
    sealing_seconds = time.perf_counter() - started
    for key in ("opened_paths", "bytes_read", "hash_count", "python_parse_count", "tree_parse_count"):
        assert small_counts[key] == large_counts[key]
    if os.environ.get("PLAN_CHANGE_LARGE_REPO") == "1":
        assert sealing_seconds < 3.0
