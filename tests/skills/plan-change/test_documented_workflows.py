from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

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
    assert text.index("references/glossary.md") < text.index("scripts/prepare_plan.py")


@pytest.mark.parametrize(
    ("marker", "fixture_name", "tier", "intent", "anchor", "risk_domains", "request_text"),
    [
        (
            "tiny-plan",
            "tiny",
            "tiny",
            "bug-fix",
            "src/names.py:normalize_name",
            [],
            "Fix normalize_name so None returns an empty string while preserving non-null normalization.",
        ),
        (
            "standard-plan",
            "typescript-standard",
            "standard",
            "refactor",
            "src/parser.ts:parseValue",
            [],
            "Rename parseValue across its re-export and consumers while preserving parser behavior.",
        ),
        (
            "high-risk-plan",
            "standard",
            "high-risk",
            "bug-fix",
            "src/flags.py:flags_for",
            ["security"],
            "Prevent cross-tenant feature-flag cache reuse while preserving same-tenant caching.",
        ),
    ],
)
def test_inline_worked_examples_pass_draft_and_finalized_validation(
    tmp_path: Path,
    marker: str,
    fixture_name: str,
    tier: str,
    intent: str,
    anchor: str,
    risk_domains: list[str],
    request_text: str,
) -> None:
    skill = ROOT / "skills" / "engineering" / "plan-change"
    fixture = ROOT / "tests" / "skills" / "plan-change" / "fixtures" / fixture_name
    text = (skill / "references" / "worked-examples.md").read_text(encoding="utf-8")
    match = re.search(
        rf"<!-- {re.escape(marker)}:start -->\n```markdown\n(.*?)\n```\n<!-- {re.escape(marker)}:end -->",
        text,
        re.DOTALL,
    )
    assert match is not None

    request = tmp_path / "request.md"
    request.write_text(request_text + "\n", encoding="utf-8")
    run_dir = tmp_path / "run"
    prepare_command = [
        sys.executable,
        str(skill / "scripts" / "prepare_plan.py"),
        "--repo-root",
        str(fixture),
        "--request-file",
        str(request),
        "--run-dir",
        str(run_dir),
        "--tier",
        tier,
        "--intent",
        intent,
        "--anchor",
        anchor,
    ]
    for domain in risk_domains:
        prepare_command.extend(["--risk-domain", domain])
    subprocess.run(prepare_command, check=True)

    plan = tmp_path / f"{marker}-example.md"
    plan.write_text(match.group(1) + "\n", encoding="utf-8")
    common = [
        "--tier",
        tier,
        "--repo-root",
        str(fixture),
        "--baseline",
        str(run_dir / "baseline.json"),
        "--inventory",
        str(run_dir / "inventory.json"),
    ]
    draft_result = subprocess.run(
        [
            sys.executable,
            str(skill / "scripts" / "check_plan.py"),
            *common,
            "--format",
            "json",
            str(plan),
        ],
        capture_output=True,
        text=True,
    )
    expected = {
        "valid": True,
        "contract_version": 5,
        "diagnostics": [],
    }
    assert draft_result.returncode == 0, f"{draft_result.stdout}\n{draft_result.stderr}"
    assert json.loads(draft_result.stdout) == expected

    finalized_result = subprocess.run(
        [
            sys.executable,
            str(skill / "scripts" / "finalize_plan.py"),
            *common,
            str(plan),
        ],
        capture_output=True,
        text=True,
    )
    assert finalized_result.returncode == 0, finalized_result.stderr
    finalized = tmp_path / f"{marker}-finalized.md"
    finalized.write_text(finalized_result.stdout, encoding="utf-8")
    receipt_result = subprocess.run(
        [
            sys.executable,
            str(skill / "scripts" / "check_plan.py"),
            *common,
            "--require-finalized",
            "--format",
            "json",
            str(finalized),
        ],
        capture_output=True,
        text=True,
    )
    assert receipt_result.returncode == 0, f"{receipt_result.stdout}\n{receipt_result.stderr}"
    assert json.loads(receipt_result.stdout) == expected


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


def test_non_python_worked_example_hashes_match_fixtures() -> None:
    text = (
        ROOT / "skills" / "engineering" / "plan-change" / "references" / "worked-examples.md"
    ).read_text(encoding="utf-8")
    fixture_root = ROOT / "tests" / "skills" / "plan-change" / "fixtures"
    cases = [
        ("typescript-tiny/src/names.ts", 1, 3),
        ("typescript-standard/src/parser.ts", 1, 3),
        ("typescript-standard/src/index.ts", 1, 1),
        ("kotlin-tiny/src/Names.kt", 1, 3),
        ("kotlin-standard/src/internal/Parser.kt", 3, 5),
        ("kotlin-standard/src/api/ParserApi.kt", 1, 5),
    ]
    for relative, start, end in cases:
        path = fixture_root / relative
        lines = path.read_text(encoding="utf-8").splitlines()
        excerpt = "\n".join(lines[start - 1 : end]) + "\n"
        assert hashlib.sha256(excerpt.encode()).hexdigest() in text
        assert hashlib.sha256(path.read_bytes()).hexdigest() in text
