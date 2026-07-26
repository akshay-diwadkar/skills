from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "skills" / "engineering" / "plan-change" / "scripts"
sys.path.insert(0, str(SCRIPTS))
from plan_runtime import _binding_diagnostics, _snapshot_diagnostics  # noqa: E402


def test_snapshot_failures_are_itemized() -> None:
    baseline = {
        "repository_id": "repo",
        "git": True,
        "git_head": "a",
        "dirty": {"dirty.py": "a"},
        "tracked": {"src.py": "a"},
        "untracked": {},
    }
    current = {
        "repository_id": "repo",
        "git": True,
        "git_head": "b",
        "dirty": {"dirty.py": "b"},
        "tracked": {"src.py": "b"},
        "untracked": {"new.py": "c"},
    }
    codes = {item.code for item in _snapshot_diagnostics(baseline, current)}
    assert codes == {
        "snapshot.head_changed",
        "snapshot.dirty_changed",
        "snapshot.tracked_changed",
        "snapshot.untracked_changed",
    }


def test_binding_failures_identify_each_collection() -> None:
    expected = {
        "repository_id": "repo",
        "git": True,
        "plan_body_sha256": "body",
        "dirty": {},
        "evidence": [{"path": "e.py", "sha256": "a"}],
        "targets": [{"path": "t.py", "sha256": "a"}],
        "generators": [{"path": "g.py", "sha256": "a"}],
        "config": [{"path": "c.toml", "sha256": "a"}],
        "schemas": [{"path": "s.json", "sha256": "a"}],
    }
    current = {
        **expected,
        "evidence": [{"path": "e.py", "sha256": "b"}],
        "targets": [{"path": "t.py", "sha256": "b"}],
        "generators": [{"path": "g.py", "sha256": "b"}],
        "config": [{"path": "c.toml", "sha256": "b"}],
        "schemas": [{"path": "s.json", "sha256": "b"}],
    }
    codes = {item.code for item in _binding_diagnostics(expected, current)}
    assert codes == {
        "binding.evidence_stale",
        "binding.target_stale",
        "binding.generator_stale",
        "binding.config_stale",
        "binding.schema_stale",
    }
