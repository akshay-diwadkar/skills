#!/usr/bin/env python3
"""Measure and validate top-level skill instruction load offline."""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = ROOT / "benchmarks" / "reports" / "skill-top-level-load.json"
TOKENIZER_PATH = (
    ROOT / "skills" / "engineering" / "map-codebase" / "scripts" / "tokenizer" / "__init__.py"
)
MAX_TOP_LEVEL_LINES = 100
MINIMUM_AGGREGATE_REDUCTION_PERCENT = 30.0


def _tokenizer() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "skill_load_tokenizer",
        TOKENIZER_PATH,
        submodule_search_locations=[str(TOKENIZER_PATH.parent)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load tokenizer: {TOKENIZER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _measure(text: str, tokenizer: ModuleType) -> dict[str, int]:
    return {"lines": len(text.splitlines()), "tokens": tokenizer.count_tokens(text)}


def skill_paths(root: Path = ROOT) -> list[Path]:
    return sorted((root / "skills").glob("*/*/SKILL.md"))


def build_report(baseline_ref: str, root: Path = ROOT) -> dict[str, Any]:
    tokenizer = _tokenizer()
    revision = subprocess.run(
        ["git", "rev-parse", baseline_ref],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    rows: dict[str, Any] = {}
    for path in skill_paths(root):
        relative = path.relative_to(root).as_posix()
        before = subprocess.run(
            ["git", "show", f"{revision}:{relative}"],
            cwd=root,
            check=True,
            capture_output=True,
        ).stdout.decode("utf-8")
        rows[path.parent.name] = {
            "path": relative,
            "before": _measure(before, tokenizer),
            "after": _measure(path.read_text(encoding="utf-8"), tokenizer),
        }
    before_total = sum(row["before"]["tokens"] for row in rows.values())
    after_total = sum(row["after"]["tokens"] for row in rows.values())
    reduction = round((before_total - after_total) * 100 / before_total, 2)
    return {
        "schema_version": 1,
        "tokenizer": "cl100k_base (vendored, integrity-checked)",
        "baseline_revision": revision,
        "maximum_top_level_lines": MAX_TOP_LEVEL_LINES,
        "minimum_aggregate_reduction_percent": MINIMUM_AGGREGATE_REDUCTION_PERCENT,
        "before_total_tokens": before_total,
        "after_total_tokens": after_total,
        "aggregate_reduction_percent": reduction,
        "skills": rows,
    }


def validate_report(path: Path = REPORT_PATH, root: Path = ROOT) -> list[str]:
    label = path.relative_to(root) if path.is_relative_to(root) else path
    if not path.is_file():
        return [f"Missing {label}"]
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [f"{label}: invalid JSON: {exc}"]

    errors: list[str] = []
    expected_names = {item.parent.name for item in skill_paths(root)}
    rows = report.get("skills")
    if not isinstance(rows, dict) or set(rows) != expected_names:
        return [f"{label}: skills must match discovered skill packages"]

    tokenizer = _tokenizer()
    before_total = 0
    after_total = 0
    for name, row in rows.items():
        skill_path = root / row["path"]
        current = _measure(skill_path.read_text(encoding="utf-8"), tokenizer)
        if row.get("after") != current:
            errors.append(f"{label}: stale after metrics for {name}")
        before = row.get("before", {})
        if not isinstance(before.get("tokens"), int) or before["tokens"] <= 0:
            errors.append(f"{label}: invalid before tokens for {name}")
            continue
        before_total += before["tokens"]
        after_total += current["tokens"]
        if current["lines"] > MAX_TOP_LEVEL_LINES:
            errors.append(f"{row['path']}: exceeds {MAX_TOP_LEVEL_LINES} lines")
        if current["tokens"] > before["tokens"]:
            errors.append(f"{row['path']}: top-level token count increased")

    reduction = round((before_total - after_total) * 100 / before_total, 2)
    expected_summary = {
        "before_total_tokens": before_total,
        "after_total_tokens": after_total,
        "aggregate_reduction_percent": reduction,
    }
    for field, value in expected_summary.items():
        if report.get(field) != value:
            errors.append(f"{label}: stale {field}")
    if reduction < MINIMUM_AGGREGATE_REDUCTION_PERCENT:
        errors.append(
            f"{label}: aggregate reduction {reduction}% is below "
            f"{MINIMUM_AGGREGATE_REDUCTION_PERCENT}%"
        )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-ref", help="Git revision used for before metrics")
    parser.add_argument("--check", action="store_true", help="Validate the committed report")
    args = parser.parse_args()
    if args.check:
        errors = validate_report()
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        print("Skill load report is current.")
        return 0
    if not args.baseline_ref:
        parser.error("--baseline-ref is required unless --check is used")
    print(json.dumps(build_report(args.baseline_ref), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
