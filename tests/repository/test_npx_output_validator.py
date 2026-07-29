from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "validation"))

import validate_npx_output as validator  # noqa: E402


def _valid_output() -> str:
    lines = ["Found 9 skills", "Engineering Skills"]
    lines.extend(sorted(validator.EXPECTED_GROUPS["Engineering Skills"]))
    lines.append("Technical Communication Skills")
    lines.extend(sorted(validator.EXPECTED_GROUPS["Technical Communication Skills"]))
    return "\n".join(lines)


def test_accepts_expected_grouped_output() -> None:
    assert validator.validate_output(_valid_output()) == []


def test_accepts_cli_tree_prefixes() -> None:
    output = "\n".join(
        f"│    {line}" if line in set().union(*validator.EXPECTED_GROUPS.values()) else line
        for line in _valid_output().splitlines()
    )
    assert validator.validate_output(output) == []


def test_rejects_fallback_group_and_wrong_membership() -> None:
    output = _valid_output().replace("Technical Communication Skills", "General")
    errors = validator.validate_output(output)
    assert any("fallback groups" in error for error in errors)
    assert any("Technical Communication Skills" in error for error in errors)


def test_reads_utf8_and_utf16_captures(tmp_path: Path) -> None:
    for encoding in ("utf-8", "utf-16"):
        output = tmp_path / f"npx-{encoding}.txt"
        output.write_text(_valid_output(), encoding=encoding)
        assert validator.validate_output(validator.read_output_text(output)) == []
