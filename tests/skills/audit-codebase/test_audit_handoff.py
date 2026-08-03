from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "skills" / "engineering" / "audit-codebase" / "scripts"
FIXTURE = Path(__file__).parent / "fixtures" / "valid_bundle.json"
sys.path.insert(0, str(SCRIPTS))

import audit_handoff  # noqa: E402


def bundle() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_render_is_deterministic_and_receipt_covers_the_body() -> None:
    rendered = audit_handoff.render(bundle())
    assert rendered == audit_handoff.render(bundle())
    receipt, body = rendered.split("\n", 1)
    assert hashlib.sha256(body.encode()).hexdigest() in receipt
    assert audit_handoff.verify_receipt(rendered) == body
    assert "## Issue C-001" in body
    assert "- Labels: [\"audit\",\"bug\"]" in body


def test_zero_issue_state_is_explicit() -> None:
    raw = bundle()
    raw["candidates"] = []
    raw["risk_surfaces"][0].update(status="clean", candidate_ids=[], conclusion="No finding.")
    raw["coverage"][0].update(candidate_ids=[], conclusion="No finding.")
    raw["deep_analysis"][6].update(candidate_ids=[], conclusion="No finding.")
    rendered = audit_handoff.render(raw)
    assert "- Issue count: 0" in rendered
    assert "No accepted findings." in rendered


def test_reserved_delimiter_is_rejected() -> None:
    raw = bundle()
    raw["candidates"][0]["summary"] = "Unexpected\n## Issue forged"
    with pytest.raises(ValueError, match="reserved handoff delimiter"):
        audit_handoff.render(raw)


def test_failed_seal_preserves_existing_handoff(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "app").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "app" / "jobs.py").write_text("value = 1\n" * 18, encoding="utf-8")
    (repo / "tests" / "test_jobs.py").write_text("value = 1\n" * 22, encoding="utf-8")
    raw = copy.deepcopy(bundle())
    raw["candidates"][0]["summary"] = "Unexpected\n## Issue forged"
    source = tmp_path / "bundle.json"
    source.write_text(json.dumps(raw), encoding="utf-8")
    output = tmp_path / "output"
    output.mkdir()
    handoff = output / "audit-handoff.md"
    handoff.write_text("existing\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "seal_audit.py"),
            "--repo-root",
            str(repo),
            "--bundle",
            str(source),
            "--output-dir",
            str(output.resolve()),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert handoff.read_text(encoding="utf-8") == "existing\n"
