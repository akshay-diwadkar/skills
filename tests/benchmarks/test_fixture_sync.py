"""Scratch-staged fixture synchronization regression tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.generators import generate


def _write(root: Path, path: str, value: str) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(value, encoding="utf-8")


def test_file_sync_updates_and_removes_without_replacing_fixture_root(tmp_path: Path) -> None:
    staged = tmp_path / "scratch" / "generated" / "billing"
    target = tmp_path / "checkout" / "billing"
    session = tmp_path / "scratch" / "session"
    _write(staged, "same.txt", "same")
    _write(staged, "changed.txt", "new")
    _write(staged, "new/nested.txt", "created")
    _write(target, "same.txt", "same")
    _write(target, "changed.txt", "old")
    _write(target, "stale.txt", "remove")

    original_root = target.resolve()
    generate._sync_fixture(staged, target, session / "journal", session)

    assert target.resolve() == original_root
    assert (target / "changed.txt").read_text(encoding="utf-8") == "new"
    assert (target / "new/nested.txt").read_text(encoding="utf-8") == "created"
    assert not (target / "stale.txt").exists()


def test_file_sync_rolls_back_the_current_fixture_on_write_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    staged = tmp_path / "scratch" / "generated" / "billing"
    target = tmp_path / "checkout" / "billing"
    session = tmp_path / "scratch" / "session"
    _write(staged, "changed.txt", "new")
    _write(staged, "new.txt", "created")
    _write(target, "changed.txt", "old")

    original = generate._write_changed_file
    calls = 0

    def fail_on_second(source: Path, destination: Path, current_session: Path, relative: str) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated locked file")
        original(source, destination, current_session, relative)

    monkeypatch.setattr(generate, "_write_changed_file", fail_on_second)
    with pytest.raises(OSError, match="simulated"):
        generate._sync_fixture(staged, target, session / "journal", session)

    assert (target / "changed.txt").read_text(encoding="utf-8") == "old"
    assert not (target / "new.txt").exists()


def test_checkout_directory_is_never_a_recursive_cleanup_target() -> None:
    source = Path(generate._remove_tree.__code__.co_filename).read_text(encoding="utf-8")
    assert "_remove_tree(canonical)" not in source
    assert "_remove_tree(REPOS)" not in source
