from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILL = ROOT / "skills" / "engineering" / "optimize-codebase"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from report_factory import fixture_repo, valid_report  # noqa: E402


def _checker():
    scripts = SKILL / "scripts"
    sys.path.insert(0, str(scripts))
    spec = importlib.util.spec_from_file_location("handoff_only_checker", scripts / "check_optimization.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_contract_exposes_only_analysis_handoff() -> None:
    contract = json.loads((SKILL / "references" / "optimization-contract.json").read_text(encoding="utf-8"))
    protocol = json.loads((SKILL / "skill-protocol.json").read_text(encoding="utf-8"))
    assert contract["paths"] == ["full"]
    assert contract["stages"] == ["plan"]
    assert contract["handoff_states"] == ["plan-ready", "needs-evidence", "no-change"]
    assert {item["name"] for item in protocol["inputs"]} == {"draft", "output_dir", "scope"}
    assert "implementation" not in json.dumps(protocol)


def test_sealer_emits_one_typed_handoff(tmp_path: Path) -> None:
    repo = fixture_repo(tmp_path / "repo", git=True)
    draft = tmp_path / "draft.md"
    draft.write_text(valid_report(), encoding="utf-8")
    output = tmp_path / "output"
    result = subprocess.run(
        [sys.executable, str(SKILL / "scripts" / "seal_optimization.py"), "--repo-root", str(repo), "--draft", str(draft), "--output-dir", str(output), "--scope", "targeted"],
        capture_output=True,
        text=True,
        check=True,
    )
    path = output / "optimization-handoff.md"
    first, body = path.read_text(encoding="utf-8").split("\n", 1)
    assert first == f"<!-- optimization-handoff: 1; sha256: {hashlib.sha256(body.encode()).hexdigest()} -->"
    assert {item.name for item in output.iterdir()} == {"optimization-handoff.md"}
    assert json.loads(result.stdout)["path"] == str(path)


def test_terminal_handoff_is_valid_but_not_plan_ready(tmp_path: Path) -> None:
    repo = fixture_repo(tmp_path / "repo")
    assert _checker().validate(valid_report(status="needs-evidence"), "full", "targeted", "plan", repo) == []
