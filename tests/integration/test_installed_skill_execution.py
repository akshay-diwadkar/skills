from __future__ import annotations

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
