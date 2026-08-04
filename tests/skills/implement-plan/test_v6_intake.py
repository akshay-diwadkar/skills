from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
V6_RUNTIME_PATH = ROOT / "skills" / "engineering" / "implement-plan" / "scripts" / "plan_v6_runtime.py"
SCAFFOLD = ROOT / "skills" / "engineering" / "implement-plan" / "scripts" / "scaffold_implementation.py"

sys.path.insert(0, str(V6_RUNTIME_PATH.parent))
SPEC = importlib.util.spec_from_file_location("frozen_plan_v6_runtime", V6_RUNTIME_PATH)
assert SPEC and SPEC.loader
V6_RUNTIME = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = V6_RUNTIME
SPEC.loader.exec_module(V6_RUNTIME)


def test_implement_plan_accepts_current_v6_sealed_plan(tmp_path: Path) -> None:
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

<!-- plan-contract: 6 -->
<!-- plan-metadata: {"intent":"bug-fix","tier":"tiny","risk_domains":[]} -->

## Outcome
SC-1: given: an empty target input | when: target processes the value | then: it returns an empty string | unchanged: non-empty values remain stripped

## Evidence
F-1: kind: source | path: src/target.py | lines: 1-2 | anchor: target | claim: target owns string normalization

## Implementation
CH-1: path: src/target.py | anchor: target | status: existing | evidence: F-1 | change: return an empty string explicitly before stripping non-empty input values | locality: local | reversibility: reversible

## Verification
T-1: covers: SC-1, CH-1 | given: empty and non-empty values | when: targeted target tests execute | then: empty input is empty and non-empty input is stripped | command: python -m pytest tests/test_target.py -q
""",
        encoding="utf-8",
    )
    sealed = V6_RUNTIME.seal_plan(repo, request, draft)
    plan.write_text(sealed.text, encoding="utf-8")
    scaffolded = subprocess.run(
        [sys.executable, str(SCAFFOLD), "--repo-root", str(repo), "--plan", str(plan), "--output", str(bundle)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert scaffolded.returncode == 0, scaffolded.stdout + scaffolded.stderr
    value = json.loads(bundle.read_text(encoding="utf-8"))
    assert value["plan"]["normalized"]["contract_version"] == 6
    assert value["warnings"] == []
    assert value["workspace"]["targets"][0]["path"] == "src/target.py"
