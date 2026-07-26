from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FINALIZER = ROOT / "skills" / "engineering" / "implement-plan" / "scripts" / "finalize_implementation.py"


def test_in_progress_bundle_cannot_receive_receipt(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle.json"
    plan = tmp_path / "plan.md"
    bundle.write_text(json.dumps({"status": "in-progress"}), encoding="utf-8")
    plan.write_text("not consulted", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(FINALIZER), "--repo-root", str(tmp_path), "--plan", str(plan), str(bundle)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "bundle.receipt_status" in result.stdout
    assert "validation_receipt" not in bundle.read_text(encoding="utf-8")
