import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DEV_DIR = REPO_ROOT / "tests" / "skills" / "optimize-codebase-with-senior-dev"
SCRIPTS = REPO_ROOT / "skills" / "engineering" / "optimize-codebase-with-senior-dev" / "scripts"
sys.path.insert(0, str(DEV_DIR))
sys.path.insert(0, str(SCRIPTS))

from check_optimization import validate  # noqa: E402
from report_factory import valid_report  # noqa: E402


def fixture_repo(tmp_path: Path) -> Path:
    source = tmp_path / "src"
    source.mkdir()
    (source / "system.py").write_text("def current():\n    return 'stable'\n", encoding="utf-8")
    return tmp_path


def codes(text: str, scope: str, stage: str, repo_root: Path) -> set[str]:
    return {item.code for item in validate(text, scope, stage, repo_root)}


def test_valid_reports_pass_every_scope_and_stage(tmp_path: Path) -> None:
    repo = fixture_repo(tmp_path)

    assert validate(valid_report(), "targeted", "plan", repo) == []
    assert validate(valid_report("sweep"), "sweep", "plan", repo) == []
    assert validate(valid_report(investigate=True), "targeted", "plan", repo) == []
    assert validate(valid_report(stage="implementation"), "targeted", "implementation", repo) == []


def test_checker_rejects_missing_or_invalid_fact_citations(tmp_path: Path) -> None:
    text = valid_report().replace("src/system.py:1", "src/missing.py:9")

    assert "fact.path.missing" in codes(text, "targeted", "plan", tmp_path)


def test_checker_rejects_plan_stage_execution_and_missing_authorization(tmp_path: Path) -> None:
    repo = fixture_repo(tmp_path)
    text = valid_report().replace("- Authorization: plan-only", "- Authorization: explicit implementation — guessed")
    text += "- E-1: candidate: C-1 | authorization: guessed | change: changed | result: done | regression: V-1\n"

    findings = codes(text, "targeted", "plan", repo)
    assert "authorization.plan_only" in findings
    assert "execution.plan_forbidden" in findings


def test_checker_rejects_incomplete_sweep_matrix_and_excess_wave_depth(tmp_path: Path) -> None:
    repo = fixture_repo(tmp_path)
    text = valid_report("sweep").replace(
        "- CV-4: subsystem: ci | pass: build-test-ci | status: deferred | evidence: F-1 | priority: high | resume: collect representative CI timing and cache evidence\n",
        "",
    ).replace(
        "- CV-3: subsystem: ci | pass: runtime | status: rejected",
        "- CV-3: subsystem: ci | pass: runtime | status: candidate",
    ).replace(
        "- CV-2: subsystem: app | pass: build-test-ci | status: clean",
        "- CV-2: subsystem: app | pass: build-test-ci | status: candidate",
    )
    text = text.replace(
        "- CV-1: subsystem: app | pass: runtime | status: candidate",
        "- CV-1: subsystem: app | pass: runtime | status: candidate\n- CV-5: subsystem: ci | pass: build-test-ci | status: candidate | evidence: F-1 | priority: high | resume: none",
    )

    findings = codes(text, "sweep", "plan", repo)
    assert "coverage.wave.limit" in findings


def test_checker_rejects_unsupported_research_and_medium_confidence_quick_win(tmp_path: Path) -> None:
    repo = fixture_repo(tmp_path)
    text = valid_report().replace(
        "component: not-applicable | version: not-applicable | source: not-applicable",
        "component: framework | version: latest | source: https://example.com/latest",
    ).replace("confidence: high | effort: low", "confidence: medium | effort: low", 1)

    findings = codes(text, "targeted", "plan", repo)
    assert "research.version.unresolved" in findings
    assert "candidate.quick_win.ineligible" in findings


def test_checker_rejects_broken_links_and_missing_rollback(tmp_path: Path) -> None:
    repo = fixture_repo(tmp_path)
    text = valid_report().replace("verify: V-1", "verify: V-9", 1).replace(
        "rollback: restore the previous local implementation", "rollback: none", 1
    )

    findings = codes(text, "targeted", "plan", repo)
    assert "record.reference.missing" in findings
    assert "candidate.verification.missing" in findings
    assert "candidate.rollback.missing" in findings


def test_checker_requires_one_eligible_candidate_for_implementation(tmp_path: Path) -> None:
    repo = fixture_repo(tmp_path)
    text = valid_report(stage="implementation").replace("candidate: C-1 | authorization: user requested", "candidate: C-2 | authorization: user requested")

    assert "execution.candidate.ineligible" in codes(text, "targeted", "implementation", repo)


def test_checker_enforces_deterministic_candidate_order(tmp_path: Path) -> None:
    repo = fixture_repo(tmp_path)
    text = valid_report()
    lines = text.splitlines()
    first = next(index for index, line in enumerate(lines) if line.startswith("- C-1:"))
    second = next(index for index, line in enumerate(lines) if line.startswith("- C-2:"))
    lines[first], lines[second] = lines[second], lines[first]

    assert "candidate.order.invalid" in codes("\n".join(lines) + "\n", "targeted", "plan", repo)


def test_checker_rejects_fabricated_static_and_percentage_only_measurements(tmp_path: Path) -> None:
    repo = fixture_repo(tmp_path)
    static_claim = valid_report(static=True).replace(
        "three duplicated policy branches across one change path",
        "20% faster by inspection",
    )
    percentage_only = valid_report().replace(
        "median 40 ms across five warm runs",
        "20% faster",
    )

    assert "baseline.static.performance_claim" in codes(static_claim, "targeted", "plan", repo)
    assert "baseline.percentage_only" in codes(percentage_only, "targeted", "plan", repo)
