from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any

from check_manual import validate_manual


def types(text: str, bundle: dict[str, Any], repo: Path) -> set[str]:
    return {item["type"] for item in validate_manual(text, bundle, repo)}


def test_semantic_drift_and_operational_gaps(manual_case: tuple[Path, Path, Path, dict[str, Any]]) -> None:
    repo, _manual, _bundle_path, base = manual_case
    bundle = copy.deepcopy(base)
    bundle["required_facts"] = [{"id": "FACT-1", "claim": "Port 8080 is required.", "source_ids": ["SRC-1"]}]
    bundle["integrity_literals"] = [
        {"id": "LIT-1", "kind": "command", "literal": "tool --mode safe --port 8080", "source_ids": ["SRC-1"]},
        {"id": "LIT-2", "kind": "path", "literal": "/srv/app", "source_ids": ["SRC-1"]},
        {"id": "LIT-3", "kind": "value", "literal": "enabled", "source_ids": ["SRC-1"]},
    ]
    bundle["procedures"] = [{"id": "PROC-1", "ordered_markers": ["First step.", "Second step."]}]
    bundle["warnings"] = [{"id": "WARN-1", "warning": "WARNING: Stop causes downtime.", "dangerous_action": "Stop the service."}]
    bundle["recovery_steps"] = [{"id": "REC-1", "trigger": "If startup fails", "step": "Restore the backup."}]
    bundle["prerequisites"] = [{"id": "PRE-1", "marker": "Administrator access is required."}]
    bundle["branches"] = [{"id": "BR-1", "condition": "If the host is offline", "required_markers": ["Use the console."]}]
    text = """tool --port 8080 --mode safe
Second step.
First step.
Stop the service.
WARNING: Stop causes downtime.
"""
    assert {
        "missing_required_fact",
        "changed_command",
        "missing_path",
        "missing_value",
        "procedure_order",
        "warning_order",
        "missing_recovery_step",
        "missing_prerequisite",
        "missing_branch",
        "incomplete_branch",
    } <= types(text, bundle, repo)


def test_source_hash_and_path_safety(manual_case: tuple[Path, Path, Path, dict[str, Any]]) -> None:
    repo, manual, _bundle_path, base = manual_case
    stale = copy.deepcopy(base)
    stale["sources"][0]["sha256"] = "0" * 64
    assert "source_hash_mismatch" in types(manual.read_text(), stale, repo)

    escaping = copy.deepcopy(base)
    escaping["sources"][0]["path"] = "../source.txt"
    assert "unsafe_source_path" in types(manual.read_text(), escaping, repo)


def test_validators_are_read_only(manual_case: tuple[Path, Path, Path, dict[str, Any]]) -> None:
    repo, manual, bundle_path, bundle = manual_case
    paths = [manual, bundle_path, repo / "source.txt"]
    before = {path: (path.read_bytes(), os.stat(path).st_mtime_ns) for path in paths}
    assert validate_manual(manual.read_text(encoding="utf-8"), bundle, repo) == []
    after = {path: (path.read_bytes(), os.stat(path).st_mtime_ns) for path in paths}
    assert after == before
