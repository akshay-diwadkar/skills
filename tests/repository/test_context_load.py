from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "validation"))

import measure_context_load as context_load  # noqa: E402


def report() -> dict:
    return json.loads((ROOT / "benchmarks" / "reports" / "context-load.json").read_text(encoding="utf-8"))


def config() -> dict:
    return json.loads((ROOT / "benchmarks" / "context-load-budgets.json").read_text(encoding="utf-8"))


def test_report_covers_every_skill_and_every_reference_file() -> None:
    measured = report()
    names = {path.parent.name for path in context_load.skill_paths()}
    assert set(measured["skills"]) == names
    for name, row in measured["skills"].items():
        skill = ROOT / Path(row["path"]).parent
        expected = {
            path.relative_to(skill).as_posix()
            for path in (skill / "references").rglob("*")
            if path.is_file()
        }
        assert set(row["worst_reference_paths"]) == expected, name
    assert "references/plan-contract.json" in measured["skills"]["plan-change"]["worst_reference_paths"]


def test_runtime_normalization_removes_machine_paths_and_is_separator_independent() -> None:
    payload = {
        "argv": [r"C:\repo\skill\scripts\cli.py", r"C:\temp\run"],
        "cwd": r"C:\repo",
    }
    substitutions = [
        (r"C:\repo\skill", "{skill_dir}"),
        (r"C:\temp\run", "{run_dir}"),
        (r"C:\repo", "{repo_root}"),
    ]
    assert context_load._normalize_value(payload, substitutions) == {
        "argv": ["{skill_dir}/scripts/cli.py", "{run_dir}"],
        "cwd": "{repo_root}",
    }
    with pytest.raises(ValueError, match="absolute path"):
        context_load._normalize_value({"python": "/opt/python/bin/python"}, [])


def test_text_hashes_are_independent_of_checkout_line_endings(tmp_path: Path) -> None:
    lf = tmp_path / "lf.json"
    crlf = tmp_path / "crlf.json"
    lf.write_bytes(b'{"value": 1}\n')
    crlf.write_bytes(b'{"value": 1}\r\n')
    assert context_load._sha256_file(lf) == context_load._sha256_file(crlf)


def test_phase_measurement_follows_transitive_and_conditional_references(tmp_path: Path) -> None:
    skill = tmp_path / "fixture"
    references = skill / "references"
    references.mkdir(parents=True)
    (references / "a.md").write_text("[contract](b.json)\n", encoding="utf-8")
    (references / "b.json").write_text('{"contract": true}\n', encoding="utf-8")
    (references / "c.md").write_text("conditional\n", encoding="utf-8")
    manifest = {
        "phases": {
            "drafting": {
                "required_reads": ["{skill_dir}/references/a.md"],
                "conditional_reads": [
                    {
                        "input": "tier",
                        "values": ["high-risk"],
                        "paths": ["{skill_dir}/references/c.md"],
                    }
                ],
            }
        }
    }
    measured = context_load._phase_measurements(skill, manifest, context_load._tokenizer())["drafting"]
    assert measured["required"]["paths"] == ["references/a.md", "references/b.json"]
    assert measured["conditional"][0]["paths"] == ["references/c.md"]
    assert measured["worst"]["tokens"] == (
        measured["required"]["tokens"] + measured["conditional"][0]["tokens"]
    )


def test_non_utf8_reference_is_rejected(tmp_path: Path) -> None:
    binary = tmp_path / "contract.bin"
    binary.write_bytes(b"\xff\xfe")
    with pytest.raises(ValueError, match="UTF-8"):
        context_load._read_utf8(binary)


def test_absolute_budget_overrun_blocks_and_current_exceptions_are_used() -> None:
    measured = report()
    budgets = config()
    assert context_load.budget_errors(measured, budgets) == []
    broken = copy.deepcopy(measured)
    broken["skills"]["audit-codebase"]["metrics"]["top_level"] = 751
    assert any("audit-codebase: top_level" in error for error in context_load.budget_errors(broken, budgets))


def test_delta_growth_and_large_unexplained_reduction_block() -> None:
    base = report()
    budgets = config()
    grown = copy.deepcopy(base)
    grown["skills"]["audit-codebase"]["metrics"]["top_level"] += 33
    assert any("increased by 33" in error for error in context_load.delta_errors(grown, base, budgets))

    reduced = copy.deepcopy(base)
    previous = reduced["skills"]["audit-codebase"]["metrics"]["worst_references"]
    allowance = max(
        budgets["delta_budgets"]["worst_references"],
        int(previous * budgets["large_reduction_percent"] / 100),
    )
    reduced["skills"]["audit-codebase"]["metrics"]["worst_references"] -= allowance + 1
    assert any("content-reduction exception" in error for error in context_load.delta_errors(reduced, base, budgets))


def test_stale_and_expired_exceptions_are_rejected() -> None:
    measured = report()
    budgets = config()
    stale = copy.deepcopy(budgets)
    stale["exceptions"].append(
        {
            "id": "unused-audit-exception",
            "skill": "audit-codebase",
            "metric": "worst_references",
            "direction": "increase",
            "max_tokens": 9000,
            "expires": "2099-01-01",
            "rationale": "Fixture used to prove stale exception rejection.",
            "supporting_paths": ["references/audit-protocol.md"],
            "protected_rule_ids": ["audit.read-only"],
        }
    )
    assert any("unused-audit-exception" in error for error in context_load.budget_errors(measured, stale))

    expired = copy.deepcopy(budgets)
    expired["exceptions"][0]["expires"] = "2000-01-01"
    assert any("expired" in error for error in context_load._validate_config(expired, ROOT))


def test_summary_reports_per_skill_totals_and_changes() -> None:
    measured = report()
    base = copy.deepcopy(measured)
    measured["skills"]["manualize"]["metrics"]["worst_context"] += 5
    summary = context_load.markdown_summary(measured, base)
    assert "| manualize |" in summary
    assert "| +5 |" in summary


def test_stale_report_diagnostics_name_changed_fields() -> None:
    expected = {"skills": {"fixture": {"metrics": {"top_level": 10}}}}
    actual = {"skills": {"fixture": {"metrics": {"top_level": 11}}}}
    assert context_load._report_differences(expected, actual) == [
        "report.skills.fixture.metrics.top_level: committed 10, measured 11"
    ]
