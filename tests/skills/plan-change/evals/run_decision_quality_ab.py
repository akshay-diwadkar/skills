#!/usr/bin/env python3
"""Run provider-neutral weaker/stronger A/B evaluations for plan-change."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
SKILL_ROOT = ROOT / "skills" / "engineering" / "plan-change"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
from plan_runtime import Plan, parse_plan  # noqa: E402

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixtures" / "decision-quality-decimal"
RUBRIC = HERE / "decision_quality_rubric.json"


def run_adapter(command: list[str], request: dict[str, Any]) -> str:
    result = subprocess.run(
        command,
        input=json.dumps(request),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(f"adapter exited {result.returncode}: {result.stderr.strip()}")
    response = json.loads(result.stdout)
    if not isinstance(response, dict) or not isinstance(response.get("plan_markdown"), str):
        raise RuntimeError("adapter stdout must be JSON with string plan_markdown")
    return str(response["plan_markdown"])


def _record_text(plan: Plan, kind: str, fields: tuple[str, ...]) -> str:
    return " ".join(
        record.fields.get(field, "")
        for record in plan.records.get(kind, ())
        for field in fields
    ).casefold()


def score_decision_quality(plan_text: str, rubric: dict[str, Any]) -> dict[str, Any]:
    plan, diagnostics = parse_plan(plan_text)
    if plan is None or diagnostics:
        return {
            "score": 0.0,
            "dimensions": {"root_cause": 0.0, "smallest_fix": 0.0, "propagation": 0.0},
            "failed_checks": ["plan:parse"],
        }
    failed: list[str] = []
    root = dict(rubric["root_cause"])
    fact_paths = {record.fields.get("path", "") for record in plan.records.get("F", ())}
    fact_anchors = {record.fields.get("anchor", "") for record in plan.records.get("F", ())}
    root_text = _record_text(plan, "F", ("observation",)) + " " + _record_text(
        plan, "D", ("selected", "rejected", "drawback")
    )
    root_checks = {
        f"path:{root['path']}": root["path"] in fact_paths,
        f"anchor:{root['anchor']}": root["anchor"] in fact_anchors,
        **{f"term:{term}": str(term).casefold() in root_text for term in root["terms"]},
    }
    smallest = dict(rubric["smallest_fix"])
    changed_paths = {record.fields.get("path", "") for record in plan.records.get("CH", ())}
    selected_text = _record_text(plan, "D", ("selected",))
    smallest_checks = {
        f"required:{smallest['required_path']}": smallest["required_path"] in changed_paths,
        "allowed-paths-only": changed_paths <= set(smallest["allowed_paths"]),
        "selected-fix": any(str(term).casefold() in selected_text for term in smallest["selected_terms_any"]),
        **{f"forbidden:{path}": path not in changed_paths for path in smallest["forbidden_paths"]},
    }
    propagation = dict(rubric["propagation"])
    facts_by_id = {
        record.id: record.fields.get("path", "") for record in plan.records.get("F", ())
    }
    propagation_rows = [
        (
            facts_by_id.get(record.fields.get("because", ""), ""),
            record.fields.get("surface", ""),
        )
        for record in plan.records.get("P", ())
    ]
    propagation_checks = {
        f"path:{path}": any(row_path == path for row_path, _surface in propagation_rows)
        for path in propagation["paths"]
    }
    propagation_checks.update(
        {
            f"surface:{surface}": any(row_surface == surface for _path, row_surface in propagation_rows)
            for surface in propagation["surfaces"]
        }
    )
    checks_by_dimension = {
        "root_cause": root_checks,
        "smallest_fix": smallest_checks,
        "propagation": propagation_checks,
    }
    dimensions: dict[str, float] = {}
    for dimension, checks in checks_by_dimension.items():
        dimensions[dimension] = round(100 * sum(checks.values()) / len(checks), 2)
        failed.extend(f"{dimension}:{name}" for name, passed in checks.items() if not passed)
    return {
        "score": round(mean(dimensions.values()), 2),
        "dimensions": dimensions,
        "failed_checks": failed,
    }


def _check_plan(plan_text: str, repo: Path, run_dir: Path, tier: str) -> tuple[bool, list[str]]:
    plan_path = run_dir / "adapter-plan.md"
    plan_path.write_text(plan_text, encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "check_plan.py"),
            "--tier",
            tier,
            "--repo-root",
            str(repo),
            "--baseline",
            str(run_dir / "baseline.json"),
            "--inventory",
            str(run_dir / "inventory.json"),
            "--require-finalized",
            "--format",
            "json",
            str(plan_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        payload = json.loads(result.stdout)
        codes = [
            str(item.get("code", "unknown"))
            for item in payload.get("diagnostics", [])
            if isinstance(item, dict)
        ]
        return bool(payload.get("valid")) and result.returncode == 0, codes
    except json.JSONDecodeError:
        return False, ["check_plan.invalid_output"]


def _copy_fixture(destination: Path) -> None:
    shutil.copytree(
        FIXTURE,
        destination,
        ignore=lambda _directory, names: {"prompt.md"} if "prompt.md" in names else set(),
    )


def evaluate(
    adapter: list[str],
    weaker_model: str,
    stronger_model: str,
    output: Path,
    repetitions: int = 1,
) -> dict[str, Any]:
    if not weaker_model or not stronger_model or weaker_model == stronger_model:
        raise ValueError("weaker and stronger model labels must be non-empty and distinct")
    rubric = json.loads(RUBRIC.read_text(encoding="utf-8"))
    prompt = (FIXTURE / "prompt.md").read_text(encoding="utf-8")
    runs: list[dict[str, Any]] = []
    for capability, model_label in (("weaker", weaker_model), ("stronger", stronger_model)):
        for attempt in range(1, repetitions + 1):
            for condition, load_skill in (("without-skill", False), ("with-skill", True)):
                with tempfile.TemporaryDirectory(prefix="plan-change-decision-eval-") as temp:
                    temp_root = Path(temp)
                    repo = temp_root / "repo"
                    _copy_fixture(repo)
                    request_path = temp_root / "request.md"
                    request_path.write_text(prompt, encoding="utf-8")
                    run_dir = temp_root / "run"
                    prepared = subprocess.run(
                        [
                            sys.executable,
                            str(SCRIPTS / "prepare_plan.py"),
                            "--repo-root",
                            str(repo),
                            "--request-file",
                            str(request_path),
                            "--run-dir",
                            str(run_dir),
                            "--tier",
                            str(rubric["tier"]),
                            "--intent",
                            str(rubric["intent"]),
                            "--anchor",
                            str(rubric["anchor"]),
                        ],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    if prepared.returncode:
                        raise RuntimeError(f"prepare_plan.py failed: {prepared.stderr.strip()}")
                    before = sorted(
                        (path.relative_to(repo).as_posix(), path.read_bytes())
                        for path in repo.rglob("*")
                        if path.is_file()
                    )
                    request = {
                        "scenario": rubric["scenario"],
                        "repo_root": str(repo),
                        "prompt": prompt,
                        "model_label": model_label,
                        "capability": capability,
                        "condition": condition,
                        "load_skill": load_skill,
                        "skill_root": str(SKILL_ROOT) if load_skill else None,
                        "planning": {
                            "tier": rubric["tier"],
                            "intent": rubric["intent"],
                            "anchor": rubric["anchor"],
                            "baseline": str(run_dir / "baseline.json"),
                            "inventory": str(run_dir / "inventory.json"),
                            "draft": str(run_dir / "draft.md"),
                        },
                    }
                    plan_text = run_adapter(adapter, request)
                    after = sorted(
                        (path.relative_to(repo).as_posix(), path.read_bytes())
                        for path in repo.rglob("*")
                        if path.is_file()
                    )
                    grounding_valid, diagnostic_codes = _check_plan(
                        plan_text, repo, run_dir, str(rubric["tier"])
                    )
                    decision = score_decision_quality(plan_text, rubric)
                    runs.append(
                        {
                            "model_label": model_label,
                            "capability": capability,
                            "condition": condition,
                            "attempt": attempt,
                            "schema_grounding_score": 100 if grounding_valid else 0,
                            "schema_grounding_valid": grounding_valid,
                            "diagnostic_codes": diagnostic_codes,
                            "decision_quality_score": decision["score"],
                            "decision_quality_dimensions": decision["dimensions"],
                            "decision_quality_failures": decision["failed_checks"],
                            "repository_mutation": before != after,
                        }
                    )
    paired_deltas: list[dict[str, Any]] = []
    for capability, model_label in (("weaker", weaker_model), ("stronger", stronger_model)):
        for attempt in range(1, repetitions + 1):
            pair = {
                str(run["condition"]): run
                for run in runs
                if run["model_label"] == model_label and run["attempt"] == attempt
            }
            paired_deltas.append(
                {
                    "model_label": model_label,
                    "capability": capability,
                    "attempt": attempt,
                    "schema_grounding_delta": pair["with-skill"]["schema_grounding_score"]
                    - pair["without-skill"]["schema_grounding_score"],
                    "decision_quality_delta": pair["with-skill"]["decision_quality_score"]
                    - pair["without-skill"]["decision_quality_score"],
                }
            )
    report = {
        "scenario": rubric["scenario"],
        "adapter_protocol": "provider-neutral-json-v1",
        "runs": runs,
        "paired_deltas": paired_deltas,
        "aggregate_deltas": {
            "schema_grounding": round(mean(row["schema_grounding_delta"] for row in paired_deltas), 2),
            "decision_quality": round(mean(row["decision_quality_delta"] for row in paired_deltas), 2),
        },
        "live_score_movement": "measured",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter", nargs="+", required=True)
    parser.add_argument("--weaker-model", required=True)
    parser.add_argument("--stronger-model", required=True)
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    evaluate(args.adapter, args.weaker_model, args.stronger_model, args.output, args.repetitions)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
