from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILL = ROOT / "skills" / "research" / "ideate"
IDEATE_TEST_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(IDEATE_TEST_DIR))

from test_ideas_sealer import _valid_draft as _valid_draft_text  # noqa: E402, I001


def test_doctor_succeeds(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(SKILL / "scripts" / "cli.py"),
            "--repo-root", str(tmp_path),
            "--format", "json",
            "doctor",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data.get("status") == "ready"


def test_stateless_run(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    draft = tmp_path / "draft.md"
    draft.write_text(_valid_draft_text(), encoding="utf-8")
    output = tmp_path / "output"
    output.mkdir()

    result = subprocess.run(
        [
            sys.executable,
            str(SKILL / "scripts" / "cli.py"),
            "--repo-root", str(repo),
            "--input", f"draft={draft}",
            "--input", f"output_dir={output}",
            "--format", "json",
            "run",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    data = json.loads(result.stdout)
    assert data.get("status") == "complete"


def test_missing_input_draft(tmp_path: Path) -> None:
    output = tmp_path / "output"
    result = subprocess.run(
        [
            sys.executable,
            str(SKILL / "scripts" / "cli.py"),
            "--repo-root", str(tmp_path),
            "--input", f"output_dir={output}",
            "--format", "json",
            "run",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0


def test_invocation_metadata() -> None:
    import re
    skill_md = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert "disable-model-invocation: false" in skill_md
    assert "user-invocable: true" in skill_md
    version_m = re.search(r"^version:\s*(.+)$", skill_md, re.MULTILINE)
    assert version_m is not None
    assert version_m.group(1).strip() == "2.0.0"


def test_vendored_runtime_matches_canonical() -> None:
    canonical = ROOT / "tools" / "skill_protocol" / "runtime.py"
    vendored = SKILL / "scripts" / "_skill_protocol_runtime.py"
    assert canonical.is_file(), "canonical runtime missing"
    assert vendored.is_file(), "vendored runtime missing"
    assert canonical.read_bytes() == vendored.read_bytes(), "vendored runtime is stale"


def test_vendored_diagnostics_matches_canonical() -> None:
    canonical = ROOT / "tools" / "diagnostics" / "runtime.py"
    vendored = SKILL / "scripts" / "_diagnostic_contract.py"
    assert canonical.is_file(), "canonical diagnostic runtime missing"
    assert vendored.is_file(), "vendored diagnostic missing"
    assert canonical.read_bytes() == vendored.read_bytes(), "vendored diagnostics is stale"
