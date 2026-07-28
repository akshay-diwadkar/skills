from __future__ import annotations

import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
DEV_DIR = REPO_ROOT / "tests" / "skills" / "optimize-codebase"
OPTIMIZE_SCRIPTS = REPO_ROOT / "skills" / "engineering" / "optimize-codebase" / "scripts"
PLAN_SCRIPTS = REPO_ROOT / "skills" / "engineering" / "plan-change" / "scripts"
CASES_DIR = DEV_DIR / "static-regression-cases"
sys.path.insert(0, str(PLAN_SCRIPTS))
sys.path.insert(0, str(OPTIMIZE_SCRIPTS))
sys.path.insert(0, str(DEV_DIR))

from check_optimization import validate  # noqa: E402
from plan_inventory import build_inventory  # noqa: E402
from report_factory import valid_handoff, valid_report  # noqa: E402


@dataclass(frozen=True)
class StaticCase:
    execution_path: str
    scope: str
    stage: str
    required: tuple[str, ...]
    forbidden: tuple[str, ...] = ()
    handoff: bool = False
    tracked_fixture: bool = False


CASES = {
    "hot-path-decoy": StaticCase(
        "full",
        "targeted",
        "plan",
        ("- Selected candidate: C-1", "change: add shared caching", "target: C-2 | status: rejected"),
        ("band: quick-win | impact: high | confidence: high | effort: low | risk: low | verification-strength: strong | blast-radius: low | reversible: yes | independent: yes | gates: target=yes, baseline=yes, behavior=yes, compatibility=yes, verification=yes, rollback=yes, operational-cost=yes, decisions=yes | evidence: F-1, B-1, R-1 | anchors: src/system.py:current | change: add shared caching",),
    ),
    "unsupported-version": StaticCase(
        "full",
        "targeted",
        "plan",
        ("framework==1.4.0", "band: investigate", "compatibility=no", "unsupported"),
        ("band: quick-win",),
    ),
    "sweep-depth": StaticCase(
        "full",
        "sweep",
        "plan",
        ("- Sweep status: incomplete", "status: deferred", "resume: collect three representative CI timings"),
    ),
    "medium-confidence": StaticCase(
        "full",
        "targeted",
        "plan",
        ("confidence: medium", "band: investigate", "baseline=no", "compatibility=no"),
        ("band: quick-win",),
    ),
    "inconclusive-result": StaticCase(
        "full",
        "targeted",
        "implementation",
        ("median 40 ms", "median 42 ms", "inconclusive", "rollback selected"),
        ("optimization succeeded",),
    ),
    "static-maintainability": StaticCase(
        "full",
        "targeted",
        "plan",
        ("method: static", "three duplicated policy branches", "maintainability"),
        ("20% faster",),
    ),
    "authorization-routing": StaticCase(
        "full",
        "targeted",
        "plan",
        ("- Authorization: plan-only", "- H-1: stage: plan"),
        ("## Execution Record", "implementation complete"),
    ),
    "authorized-implementation": StaticCase(
        "fast",
        "targeted",
        "implementation",
        ("- Authorization: explicit implementation", "band: quick-win", "anchors: src/system.py:normalize_items"),
        tracked_fixture=True,
    ),
    "ci-trust": StaticCase(
        "full",
        "targeted",
        "plan",
        ("Preserve coverage, type checking, release gates", "change: skip tests", "target: C-2 | status: rejected"),
    ),
    "investigate-compatibility": StaticCase(
        "full",
        "targeted",
        "plan",
        ("connection pooling", "band: investigate", "baseline=no", "compatibility=no"),
        ("band: quick-win",),
    ),
    "measured-runtime": StaticCase(
        "full",
        "targeted",
        "plan",
        ("band: strategic-win", "- H-1: stage: plan | next: plan-change", "anchors: src/system.py:load_users"),
        handoff=True,
    ),
}


def _git_fixture(source: Path, destination: Path) -> Path:
    shutil.copytree(source, destination)
    subprocess.run(["git", "init", "-q"], cwd=destination, check=True)
    subprocess.run(["git", "config", "user.email", "tests@example.com"], cwd=destination, check=True)
    subprocess.run(["git", "config", "user.name", "Tests"], cwd=destination, check=True)
    subprocess.run(["git", "add", "."], cwd=destination, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=destination, check=True)
    return destination


@pytest.mark.parametrize("case_id", CASES)
def test_static_regression_case_validates(case_id: str, tmp_path: Path) -> None:
    case = CASES[case_id]
    case_dir = CASES_DIR / case_id
    report = (case_dir / "report.md").read_text(encoding="utf-8")
    repo = case_dir / "repo"
    if case.tracked_fixture:
        repo = _git_fixture(repo, tmp_path / "repo")
    handoff_path = case_dir / "request.md"
    handoff = handoff_path.read_text(encoding="utf-8") if case.handoff else None

    diagnostics = validate(report, case.execution_path, case.scope, case.stage, repo, handoff)

    assert diagnostics == [], (case_id, [item.to_dict() for item in diagnostics])
    for literal in case.required:
        assert literal in report, (case_id, literal)
    for literal in case.forbidden:
        assert literal not in report, (case_id, literal)


def test_generated_handoff_anchors_are_recovered_by_plan_change_inventory(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "system.py").write_text(
        "def current():\n    return 'stable'\n",
        encoding="utf-8",
    )
    report = valid_report(strategic=True)
    request = valid_handoff(report)
    selected = re.search(r"^- H-\d+: .*?candidate: (?P<candidate>C-\d+)$", report, re.MULTILINE)
    assert selected is not None
    candidate = re.search(
        rf"^- {re.escape(selected.group('candidate'))}: .*?\| anchors: (?P<anchors>[^|]+?) \|",
        report,
        re.MULTILINE,
    )
    assert candidate is not None
    winning_anchors = {value.strip().strip("`") for value in candidate.group("anchors").split(",")}
    request_anchors = re.findall(r"^- Anchor: `(?P<anchor>[^`]+)`$", request, re.MULTILINE)

    inventory = build_inventory(repo, request, request_anchors)

    assert winning_anchors <= set(inventory["anchors"])
