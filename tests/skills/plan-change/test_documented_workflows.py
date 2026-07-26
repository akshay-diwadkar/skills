from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_worked_examples_document_valid_finalization_order_and_all_families() -> None:
    text = (
        ROOT / "skills" / "engineering" / "plan-change" / "references" / "worked-examples.md"
    ).read_text(encoding="utf-8")
    order = [
        "prepare_plan.py",
        "without `--require-finalized`",
        "finalize_plan.py",
        "check_plan.py --require-finalized",
    ]
    positions = [text.index(value) for value in order]
    assert positions == sorted(positions)
    for heading in ("Tiny", "Standard", "Security", "Concurrency", "Migration", "ownership", "Fail-closed"):
        assert heading.casefold() in text.casefold()


def test_glossary_is_required_before_prepare_plan() -> None:
    text = (
        ROOT / "skills" / "engineering" / "plan-change" / "SKILL.md"
    ).read_text(encoding="utf-8")
    assert text.index("references/glossary.md") < text.index("python scripts/prepare_plan.py")


def test_inline_tiny_example_passes_check_plan(tmp_path: Path) -> None:
    skill = ROOT / "skills" / "engineering" / "plan-change"
    fixture = ROOT / "tests" / "skills" / "plan-change" / "fixtures" / "tiny"
    text = (skill / "references" / "worked-examples.md").read_text(encoding="utf-8")
    match = re.search(
        r"<!-- tiny-plan:start -->\n```markdown\n(.*?)\n```\n<!-- tiny-plan:end -->",
        text,
        re.DOTALL,
    )
    assert match is not None

    request = tmp_path / "request.md"
    request.write_text(
        "Fix normalize_name so None returns an empty string while preserving non-null normalization.\n",
        encoding="utf-8",
    )
    run_dir = tmp_path / "run"
    subprocess.run(
        [
            sys.executable,
            str(skill / "scripts" / "prepare_plan.py"),
            "--repo-root",
            str(fixture),
            "--request-file",
            str(request),
            "--run-dir",
            str(run_dir),
            "--tier",
            "tiny",
            "--intent",
            "bug-fix",
            "--anchor",
            "src/names.py:normalize_name",
        ],
        check=True,
    )
    plan = tmp_path / "tiny-example.md"
    plan.write_text(match.group(1) + "\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(skill / "scripts" / "check_plan.py"),
            "--tier",
            "tiny",
            "--repo-root",
            str(fixture),
            "--baseline",
            str(run_dir / "baseline.json"),
            "--inventory",
            str(run_dir / "inventory.json"),
            "--format",
            "json",
            str(plan),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(result.stdout) == {
        "valid": True,
        "contract_version": 5,
        "diagnostics": [],
    }


def test_every_configured_evaluation_has_fixture_and_structured_expectations() -> None:
    evals = ROOT / "tests" / "skills" / "plan-change" / "evals"
    scenarios = json.loads((evals / "v5_scenarios.json").read_text())
    expectations = json.loads((evals / "expectations.json").read_text())
    names = {name for family in scenarios["scenario_families"].values() for name in family}
    assert names == set(expectations)
    assert all((evals / "fixtures" / name / "prompt.md").is_file() for name in names)
    assert all(
        {"grounding", "propagation", "decisions", "implementation", "blueprints", "verification"}
        <= set(expectations[name])
        for name in names
    )
