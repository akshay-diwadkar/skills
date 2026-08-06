"""Offline provider-free plan-quality fixture suite."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from .cases import CASES
from .scorer import RUNTIME, score_plan

REPORT_PATH = Path(__file__).resolve().parents[4] / "benchmarks" / "reports" / "plan-change-quality-v7.json"


def test_quality_suite_has_at_least_twelve_cases() -> None:
    assert len(CASES) >= 12
    assert len({case.id for case in CASES}) == len(CASES)
    assert all(len(case.weak) >= 2 for case in CASES)


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.id)
def test_golden_plans_seal_and_score_complete(case, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    case.build_repo(repo)
    request = tmp_path / "request.md"
    draft = tmp_path / "draft.md"
    request.write_bytes(case.request.encode("utf-8"))
    draft.write_text(case.golden, encoding="utf-8")
    sealed = RUNTIME.seal_plan(repo, request, draft, handoff_item=case.handoff_item)
    assert "<!-- plan-validation: 7;" in sealed.text
    report = score_plan(
        case.golden,
        repo,
        request_bytes=case.request.encode("utf-8"),
        obligation_manifest=case.obligations,
        handoff_item=case.handoff_item,
    )
    assert report.diagnostics == (), report.diagnostics
    assert report.missing_obligations == ()
    assert report.complete is True
    assert report.structural_ok is True
    assert all(report.dimensions.values())
    assert set(report.manifest_validated) == set(report.dimensions)


@pytest.mark.parametrize(
    ("case", "weak"),
    [(case, weak) for case in CASES for weak in case.weak],
    ids=lambda value: getattr(value, "id", None) or getattr(value, "name", str(value)),
)
def test_weak_plans_fail_for_intended_reason(case, weak, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    case.build_repo(repo)
    mutated = weak.mutate(case.golden)
    assert mutated != case.golden
    report = score_plan(
        mutated,
        repo,
        request_bytes=case.request.encode("utf-8"),
        obligation_manifest=case.obligations,
        handoff_item=case.handoff_item,
    )
    assert report.complete is False
    blob = (
        "\n".join(report.diagnostics)
        + "\n"
        + ",".join(report.missing_obligations)
        + "\n"
        + ",".join(name for name, ok in report.dimensions.items() if not ok)
    )
    assert weak.expected_reason in blob


def test_quality_report_artifact_contract(tmp_path: Path) -> None:
    rows: list[dict[str, Any]] = []
    for case in CASES:
        repo = tmp_path / case.id
        case.build_repo(repo)
        request = tmp_path / f"{case.id}-request.md"
        draft = tmp_path / f"{case.id}-draft.md"
        request.write_bytes(case.request.encode("utf-8"))
        draft.write_text(case.golden, encoding="utf-8")
        sealed = RUNTIME.seal_plan(repo, request, draft, handoff_item=case.handoff_item)
        assert "<!-- plan-proof:" in sealed.text
        golden = score_plan(
            case.golden,
            repo,
            request_bytes=case.request.encode("utf-8"),
            obligation_manifest=case.obligations,
            handoff_item=case.handoff_item,
        )
        weak_rows: list[dict[str, Any]] = []
        for weak in case.weak:
            weak_score = score_plan(
                weak.mutate(case.golden),
                repo,
                request_bytes=case.request.encode("utf-8"),
                obligation_manifest=case.obligations,
                handoff_item=case.handoff_item,
            )
            weak_rows.append(
                {
                    "name": weak.name,
                    "expected_reason": weak.expected_reason,
                    "complete": weak_score.complete,
                    "matched_reason": weak.expected_reason
                    in "\n".join(weak_score.diagnostics)
                    + "\n"
                    + ",".join(weak_score.missing_obligations)
                    + "\n"
                    + ",".join(name for name, ok in weak_score.dimensions.items() if not ok),
                }
            )
        rows.append(
            {
                "id": case.id,
                "golden_complete": golden.complete,
                "golden_sealed": True,
                "structural_ok": golden.structural_ok,
                "manifest_validated_dimensions": list(golden.manifest_validated),
                "weak": weak_rows,
            }
        )
    report: dict[str, Any] = {
        "schema_version": 2,
        "label": (
            "deterministic plan-quality fixtures; structural sealing is separate from "
            "manifest-validated dimensions; excludes live agents and sealing microbenchmark"
        ),
        "case_count": len(rows),
        "cases": rows,
    }
    assert report["case_count"] >= 12
    assert all(case["golden_complete"] and case["golden_sealed"] and case["structural_ok"] for case in rows)
    assert all((not item["complete"]) and item["matched_reason"] for case in rows for item in case["weak"])
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
