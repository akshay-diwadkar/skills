from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SEALER = ROOT / "skills" / "engineering" / "plan-change" / "scripts" / "seal_plan.py"
SCAFFOLD = ROOT / "skills" / "engineering" / "implement-plan" / "scripts" / "scaffold_implementation.py"
V6_RUNTIME = ROOT / "skills" / "engineering" / "implement-plan" / "scripts" / "plan_v6_runtime.py"


def test_implement_plan_accepts_current_v7_sealed_plan(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "target.py").write_text("def target(raw: str) -> str:\n    return raw.strip()\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "tests@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Tests"], cwd=repo, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=repo, check=True)
    request = tmp_path / "request.md"
    draft = tmp_path / "draft.md"
    plan = tmp_path / "plan.md"
    bundle = tmp_path / "bundle.json"
    request.write_text("Handle empty target input.\n", encoding="utf-8")
    draft.write_text(
        """# Handle empty target input

<!-- plan-contract: 7 -->
<!-- plan-metadata: {"intent":"bug-fix","tier":"tiny","risk_domains":[]} -->

## Obligations
RQ-1: source: request | anchor: empty target input | obligation: return an empty string for empty target input | covered_by: SC-1, CH-1, T-1

## Outcome
SC-1: given: an empty target input | when: target processes the value | then: it returns an empty string | unchanged: non-empty values remain stripped

## Evidence
F-1: kind: source | path: src/target.py | lines: 1-2 | anchor: target | claim: target owns string normalization

## Implementation
CH-1: path: src/target.py | anchor: target | status: existing | evidence: F-1 | change: return an empty string explicitly before stripping non-empty input values | depends_on: none | locality: local | reversibility: reversible

## Verification
T-1: covers: SC-1, CH-1 | given: empty and non-empty values | when: targeted target tests execute | then: the case fails before the fix and passes after the fix with empty input empty while non-empty input is stripped | command: python -m pytest tests/test_target.py -q
""",
        encoding="utf-8",
    )
    sealed = subprocess.run(
        [sys.executable, str(SEALER), "--repo-root", str(repo), "--request-file", str(request), "--draft", str(draft)],
        capture_output=True,
        text=True,
        check=True,
    )
    plan.write_text(sealed.stdout, encoding="utf-8")
    scaffolded = subprocess.run(
        [sys.executable, str(SCAFFOLD), "--repo-root", str(repo), "--plan", str(plan), "--output", str(bundle)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert scaffolded.returncode == 0, scaffolded.stdout + scaffolded.stderr
    value = json.loads(bundle.read_text(encoding="utf-8"))
    assert value["plan"]["normalized"]["contract_version"] == 7
    assert value["plan"]["change_order"] == ["CH-1"]
    assert value["workspace"]["change_order"] == ["CH-1"]
    assert value["warnings"] == []
    assert value["workspace"]["targets"][0]["path"] == "src/target.py"


def test_frozen_v6_runtime_still_parses_historical_marker() -> None:
    text = V6_RUNTIME.read_text(encoding="utf-8")
    assert "CONTRACT_VERSION = 6" in text
    assert "Exactly one plan-contract version 6 marker is required." in text
