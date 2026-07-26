from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "skills" / "engineering" / "plan-change" / "scripts"
sys.path.insert(0, str(SCRIPTS))
from plan_runtime import Record, _valid_directory_owner, _valid_generator_owner  # noqa: E402


def _record(ident: str, **fields: str) -> Record:
    return Record(ident, fields, 1, "Implementation Specification" if ident.startswith("CH-") else "Evidence Ledger")


def test_directory_owner_must_own_target_ancestor(tmp_path: Path) -> None:
    (tmp_path / "src" / "package").mkdir(parents=True)
    target = _record("CH-1", path="src/package/new.py", status="new")
    owner = _record("F-1", kind="directory-ownership", path="src/package/__init__.py", directory="src/package")
    unrelated = _record("F-2", kind="directory-ownership", path="other/__init__.py", directory="other")
    assert _valid_directory_owner(target, owner, tmp_path)
    assert not _valid_directory_owner(target, unrelated, tmp_path)
    assert not _valid_directory_owner(target, _record("F-3", kind="directory-ownership", path=target.fields["path"], directory="src/package"), tmp_path)


def test_generator_owner_must_declare_exact_output() -> None:
    target = _record("CH-1", path="generated/model.py", status="new")
    owner = _record(
        "F-1",
        kind="generated-from",
        path="generate.py",
        generator="generate.py",
        output="generated/model.py",
    )
    unrelated = _record(
        "F-2",
        kind="generated-from",
        path="generate.py",
        generator="generate.py",
        output="generated/other.py",
    )
    assert _valid_generator_owner(target, owner, {"F-1": owner})
    assert not _valid_generator_owner(target, unrelated, {"F-2": unrelated})
