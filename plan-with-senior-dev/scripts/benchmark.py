#!/usr/bin/env python3
"""Validate benchmark cases, create blind A/B packs, and summarize scored outputs."""

from __future__ import annotations

import argparse
import json
import random
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "evals" / "manifest.json"
DIMENSIONS = {
    "repository_truth": 25,
    "decision_completeness": 25,
    "propagation_constraints": 20,
    "interfaces_logic": 15,
    "tests_rollback_risk": 15,
}


@dataclass(frozen=True)
class Case:
    case_id: str
    tier: str
    fixture: Path
    prompt: str
    oracle: dict[str, Any]


def load_cases(manifest_path: Path = DEFAULT_MANIFEST) -> list[Case]:
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    base = manifest_path.parent
    cases: list[Case] = []
    for entry in raw.get("cases", []):
        case_file = base / entry["case"]
        case_raw = json.loads(case_file.read_text(encoding="utf-8"))
        cases.append(Case(
            case_id=case_raw["id"],
            tier=case_raw["tier"],
            fixture=(base / case_raw["fixture"]).resolve(),
            prompt=case_raw["prompt"],
            oracle=case_raw["oracle"],
        ))
    return cases


def validate_cases(cases: list[Case]) -> list[str]:
    errors: list[str] = []
    if len(cases) != 8:
        errors.append(f"benchmark must contain exactly 8 cases; found {len(cases)}")
    ids: set[str] = set()
    for case in cases:
        if case.case_id in ids:
            errors.append(f"duplicate case id: {case.case_id}")
        ids.add(case.case_id)
        if case.tier not in {"tiny", "standard", "high-risk"}:
            errors.append(f"{case.case_id}: invalid tier {case.tier!r}")
        if not case.fixture.is_dir():
            errors.append(f"{case.case_id}: missing fixture directory {case.fixture}")
        elif not any(path.is_file() for path in case.fixture.rglob("*")):
            errors.append(f"{case.case_id}: fixture directory is empty")
        if len(case.prompt.strip()) < 20:
            errors.append(f"{case.case_id}: prompt is too short")
        for key in ("required_facts", "forbidden_claims", "critical_failures"):
            value = case.oracle.get(key)
            if not isinstance(value, list) or not value:
                errors.append(f"{case.case_id}: oracle.{key} must be a non-empty list")
    return errors


def expected_output_names(cases: list[Case]) -> list[str]:
    return [f"{case.case_id}-{replicate}.md" for case in cases for replicate in (1, 2)]


def create_blind_pack(
    cases: list[Case], baseline: Path, candidate: Path, seed: int
) -> tuple[dict[str, Any], dict[str, str]]:
    names = expected_output_names(cases)
    missing = [
        str(root / name)
        for root in (baseline, candidate)
        for name in names
        if not (root / name).is_file()
    ]
    if missing:
        raise ValueError("missing benchmark outputs: " + ", ".join(missing))

    randomizer = random.Random(seed)
    entries: list[dict[str, Any]] = []
    reveal: dict[str, str] = {}
    for case in cases:
        for replicate in (1, 2):
            source_name = f"{case.case_id}-{replicate}.md"
            variants = [("baseline", baseline / source_name), ("candidate", candidate / source_name)]
            randomizer.shuffle(variants)
            for slot, (variant, source) in zip(("A", "B"), variants, strict=True):
                output_id = f"{case.case_id}-{replicate}-{slot}"
                reveal[output_id] = variant
                entries.append({
                    "output_id": output_id,
                    "case_id": case.case_id,
                    "tier": case.tier,
                    "fixture": str(case.fixture),
                    "prompt": case.prompt,
                    "oracle": case.oracle,
                    "plan": source.read_text(encoding="utf-8"),
                })
    return {"seed": seed, "dimensions": DIMENSIONS, "entries": entries}, reveal


def score_total(record: dict[str, Any]) -> int:
    raw_total = sum(int(record.get(name, 0)) for name in DIMENSIONS)
    total = min(raw_total, 100)
    if record.get("critical_errors"):
        total = min(total, 59)
    return total


def summarize(scores: list[dict[str, Any]], reveal: dict[str, str]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {"baseline": [], "candidate": []}
    for record in scores:
        output_id = record["output_id"]
        variant = reveal.get(output_id)
        if variant not in grouped:
            raise ValueError(f"score has unknown output_id: {output_id}")
        enriched = dict(record)
        enriched["total"] = score_total(record)
        grouped[variant].append(enriched)

    result: dict[str, Any] = {}
    for variant, records in grouped.items():
        if not records:
            raise ValueError(f"no scores supplied for {variant}")
        totals = [int(record["total"]) for record in records]
        one_shot = [
            bool(record.get("one_shot")) and not record.get("critical_errors") and int(record["total"]) >= 85
            for record in records
        ]
        result[variant] = {
            "count": len(records),
            "median": statistics.median(totals),
            "mean": statistics.fmean(totals),
            "one_shot_rate": sum(one_shot) / len(one_shot),
            "critical_failures": sum(bool(record.get("critical_errors")) for record in records),
        }
    result["delta"] = {
        "median": result["candidate"]["median"] - result["baseline"]["median"],
        "mean": result["candidate"]["mean"] - result["baseline"]["mean"],
        "one_shot_rate": result["candidate"]["one_shot_rate"] - result["baseline"]["one_shot_rate"],
    }
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate")
    pack = subparsers.add_parser("pack")
    pack.add_argument("--baseline", type=Path, required=True)
    pack.add_argument("--candidate", type=Path, required=True)
    pack.add_argument("--seed", type=int, required=True)
    pack.add_argument("--output", type=Path, required=True)
    pack.add_argument("--reveal-output", type=Path, required=True)
    report = subparsers.add_parser("summarize")
    report.add_argument("--reveal", type=Path, required=True)
    report.add_argument("--scores", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cases = load_cases(args.manifest)
    errors = validate_cases(cases)
    if errors:
        for error in errors:
            print(f"Error: {error}")
        return 1
    if args.command == "validate":
        print(f"Benchmark validation passed: {len(cases)} cases.")
        return 0
    if args.command == "pack":
        try:
            pack, reveal = create_blind_pack(cases, args.baseline, args.candidate, args.seed)
        except ValueError as exc:
            print(f"Error: {exc}")
            return 1
        args.output.write_text(json.dumps(pack, indent=2), encoding="utf-8")
        args.reveal_output.write_text(json.dumps(reveal, indent=2), encoding="utf-8")
        print(f"Wrote {len(pack['entries'])} anonymized outputs to {args.output}.")
        return 0
    reveal = json.loads(args.reveal.read_text(encoding="utf-8"))
    scores = json.loads(args.scores.read_text(encoding="utf-8"))
    print(json.dumps(summarize(scores, reveal), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
