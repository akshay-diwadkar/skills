from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "skills" / "engineering" / "plan-change" / "scripts"
sys.path.insert(0, str(SCRIPTS))
from plan_inventory import build_inventory, unresolved_candidates  # noqa: E402
from plan_runtime import parse_plan  # noqa: E402


def test_inventory_discovers_material_surfaces_and_requires_reconciliation(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "api.py").write_text("def process_order():\n    return 'ok'\n")
    (tmp_path / "tests" / "test_api.py").write_text("from src.api import process_order\n")
    inventory = build_inventory(tmp_path, "Fix process order response")
    assert {item["surface"] for item in inventory["candidates"]} >= {"direct-caller", "fixture"}
    text = '''<!-- plan-contract: 5 -->
<!-- plan-metadata: {"provisional":{"intent":"bug-fix","risk_domains":[],"tier":"tiny"},"final":{"intent":"bug-fix","risk_domains":[],"tier":"tiny"}} -->
## Evidence Ledger
- F-1: kind: test-behavior | path: tests/test_api.py | lines: 1-1 | anchor: process_order | excerpt-sha256: x | file-sha256: x | observation: caller test
## Propagation Record
- P-1: owner: CH-1 | because: F-1 | surface: fixture | disposition: changed
'''
    plan, diagnostics = parse_plan(text)
    assert plan is not None
    assert any(item.endswith("src/api.py") for item in unresolved_candidates(plan, inventory))


def test_prepare_plan_creates_only_an_isolated_workspace(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "service.py").write_text("def process_order():\n    return 'ok'\n")
    request = tmp_path / "request.md"
    request.write_text("Fix process_order response")
    run_dir = tmp_path / "run"
    result = subprocess.run(
        [sys.executable, "scripts/prepare_plan.py", "--repo-root", str(repo), "--request-file", str(request), "--run-dir", str(run_dir), "--tier", "tiny", "--intent", "bug-fix"],
        cwd=SCRIPTS.parent,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert {path.name for path in run_dir.iterdir()} == {"baseline.json", "inventory.json", "draft.md"}
    assert json.loads((run_dir / "inventory.json").read_text())["candidates"]
    assert (repo / "src" / "service.py").read_text() == "def process_order():\n    return 'ok'\n"
