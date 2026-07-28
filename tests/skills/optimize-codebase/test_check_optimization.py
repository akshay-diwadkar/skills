import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DEV_DIR = REPO_ROOT / "tests" / "skills" / "optimize-codebase"
SCRIPTS = REPO_ROOT / "skills" / "engineering" / "optimize-codebase" / "scripts"
sys.path.insert(0, str(DEV_DIR))
sys.path.insert(0, str(SCRIPTS))

from check_optimization import validate  # noqa: E402
from report_factory import valid_fast_report, valid_handoff, valid_report  # noqa: E402


def fixture_repo(tmp_path: Path, *, git: bool = False) -> Path:
    source = tmp_path / "src"
    source.mkdir()
    (source / "system.py").write_text("def current():\n    return 'stable'\n", encoding="utf-8")
    if git:
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(["git", "config", "user.email", "tests@example.com"], cwd=tmp_path, check=True)
        subprocess.run(["git", "config", "user.name", "Tests"], cwd=tmp_path, check=True)
        subprocess.run(["git", "add", "src/system.py"], cwd=tmp_path, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=tmp_path, check=True)
    return tmp_path


def codes(
    text: str,
    execution_path: str,
    scope: str,
    stage: str,
    repo_root: Path,
    handoff: str | None = None,
) -> set[str]:
    return {item.code for item in validate(text, execution_path, scope, stage, repo_root, handoff)}


def test_valid_fast_and_full_reports_pass(tmp_path: Path) -> None:
    repo = fixture_repo(tmp_path, git=True)
    strategic = valid_report(strategic=True)

    assert validate(valid_fast_report(), "fast", "targeted", "implementation", repo) == []
    assert validate(valid_report(), "full", "targeted", "plan", repo) == []
    assert validate(strategic, "full", "targeted", "plan", repo, valid_handoff(strategic)) == []
    assert validate(valid_report(investigate=True), "full", "targeted", "plan", repo) == []
    assert validate(valid_report(stage="implementation"), "full", "targeted", "implementation", repo) == []


def test_fast_requires_exact_f_b_c_records(tmp_path: Path) -> None:
    repo = fixture_repo(tmp_path, git=True)
    text = valid_fast_report().replace(
        "- C-1:",
        "- F-2: `src/system.py:1` | anchor: `current` | observation: duplicate fact.\n- C-1:",
    )

    assert "fast.records.exact" in codes(text, "fast", "targeted", "implementation", repo)


def test_fast_cannot_skip_baseline_evidence_or_verification(tmp_path: Path) -> None:
    repo = fixture_repo(tmp_path, git=True)
    missing_evidence = valid_fast_report().replace("evidence: F-1, B-1", "evidence: F-1")
    missing_verify = valid_fast_report().replace("verify: python bench.py and python -m pytest", "verify: none")

    assert "fast.evidence.invalid" in codes(missing_evidence, "fast", "targeted", "implementation", repo)
    assert "fast.verify.missing" in codes(missing_verify, "fast", "targeted", "implementation", repo)


def test_fast_rejects_non_quick_band_and_incomplete_eligibility(tmp_path: Path) -> None:
    repo = fixture_repo(tmp_path, git=True)
    wrong_band = valid_fast_report().replace("band: quick-win", "band: strategic-win")
    incomplete = valid_fast_report().replace("no-protected-domain=yes", "no-protected-domain=no")

    assert "fast.band.invalid" in codes(wrong_band, "fast", "targeted", "implementation", repo)
    assert "fast.eligibility.incomplete" in codes(incomplete, "fast", "targeted", "implementation", repo)


def test_fast_rejects_untracked_or_dirty_file(tmp_path: Path) -> None:
    repo = fixture_repo(tmp_path, git=True)
    (repo / "src" / "system.py").write_text("def current():\n    return 'changed'\n", encoding="utf-8")

    assert "fast.fact.dirty" in codes(valid_fast_report(), "fast", "targeted", "implementation", repo)


def test_full_rejects_invalid_fact_and_fabricated_static_claim(tmp_path: Path) -> None:
    repo = fixture_repo(tmp_path)
    missing = valid_report().replace("src/system.py:1", "src/missing.py:9")
    fabricated = valid_report(static=True).replace(
        "three duplicated policy branches across one bounded change path",
        "20% faster by inspection",
    )

    assert "fact.path.missing" in codes(missing, "full", "targeted", "plan", repo)
    assert "baseline.static.performance_claim" in codes(fabricated, "full", "targeted", "plan", repo)


def test_full_preserves_authorization_and_promotion_gates(tmp_path: Path) -> None:
    repo = fixture_repo(tmp_path)
    unauthorized = valid_report().replace("- Authorization: plan-only", "- Authorization: explicit implementation — guessed")
    medium_quick = valid_report().replace("confidence: high | effort: low", "confidence: medium | effort: low", 1)

    assert "authorization.plan_only" in codes(unauthorized, "full", "targeted", "plan", repo)
    assert "candidate.quick_win.ineligible" in codes(medium_quick, "full", "targeted", "plan", repo)


def test_full_preserves_sweep_depth_and_deferral_gates(tmp_path: Path) -> None:
    repo = fixture_repo(tmp_path)
    text = valid_report("sweep").replace(
        "- CV-2: subsystem: app | pass: build-test-ci | status: clean",
        "- CV-2: subsystem: app | pass: build-test-ci | status: candidate",
    ).replace(
        "- CV-3: subsystem: ci | pass: runtime | status: rejected",
        "- CV-3: subsystem: ci | pass: runtime | status: candidate",
    ).replace(
        "- CV-4: subsystem: ci | pass: build-test-ci | status: deferred",
        "- CV-4: subsystem: ci | pass: build-test-ci | status: candidate",
    )

    assert "coverage.wave.limit" in codes(text, "full", "sweep", "plan", repo, valid_handoff(text))


def test_plan_change_requires_separate_handoff_and_rejects_it_elsewhere(tmp_path: Path) -> None:
    repo = fixture_repo(tmp_path)
    strategic = valid_report(strategic=True)

    assert "handoff.file.required" in codes(strategic, "full", "targeted", "plan", repo)
    assert "handoff.file.unexpected" in codes(
        valid_report(), "full", "targeted", "plan", repo, valid_handoff(strategic)
    )


def test_handoff_validates_fields_flags_and_real_run_anchors(tmp_path: Path) -> None:
    repo = fixture_repo(tmp_path)
    report = valid_report(strategic=True)
    invalid_anchor = valid_handoff(report).replace("src/system.py:current", "src/system.py:invented")
    invalid_risk = valid_handoff(report).replace("- Risk domains: none", "- Risk domains: made-up")
    implicit = valid_handoff(report).replace("- Success criteria: Preserve output and reduce the named bounded cost.", "- Success criteria: TBD")

    assert "handoff.anchor.unbound" in codes(report, "full", "targeted", "plan", repo, invalid_anchor)
    assert "handoff.risk_domain.invalid" in codes(report, "full", "targeted", "plan", repo, invalid_risk)
    assert "handoff.field.missing" in codes(report, "full", "targeted", "plan", repo, implicit)


def test_handoff_rejects_candidate_or_evidence_mismatch(tmp_path: Path) -> None:
    repo = fixture_repo(tmp_path)
    report = valid_report(strategic=True)
    candidate = valid_handoff(report).replace("- Candidate: C-1", "- Candidate: C-2")
    evidence = valid_handoff(report).replace("- Evidence: F-1, B-1, R-1", "- Evidence: F-1")

    assert "handoff.field.mismatch" in codes(report, "full", "targeted", "plan", repo, candidate)
    assert "handoff.evidence.mismatch" in codes(report, "full", "targeted", "plan", repo, evidence)
