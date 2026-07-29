from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_installed_plan_change_scaffold_is_v5(tmp_path: Path) -> None:
    skill = ROOT / "skills" / "engineering" / "plan-change"
    result = subprocess.run(
        [sys.executable, "scripts/scaffold_plan.py", "--tier", "standard", "--intent", "feature"],
        cwd=skill,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "<!-- plan-contract: 5 -->" in result.stdout
    assert "Execution Blueprint:" in result.stdout


def test_installed_manualize_language_cli_executes(tmp_path: Path) -> None:
    skill = ROOT / "skills" / "technical-communication" / "manualize"
    glossary = tmp_path / "glossary.json"
    manual = tmp_path / "manual.md"
    glossary.write_text(json.dumps({"terms": [], "abbreviations": {}}), encoding="utf-8")
    manual.write_text("# Procedure\n\nRun the service.\n", encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            "scripts/check_manual_language.py",
            "--profile",
            "strict",
            "--glossary",
            str(glossary),
            str(manual),
        ],
        cwd=skill,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["violations"] == []
