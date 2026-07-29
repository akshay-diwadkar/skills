from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from check_manual_language import collect_diagnostics, parse_markdown

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "skills" / "technical-communication" / "manualize" / "scripts" / "check_manual_language.py"


def glossary(**updates: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "terms": [],
        "abbreviations": {},
        "action_verbs": [],
        "phrasal_verbs": [],
        "hazardous_actions": [],
    }
    value.update(updates)
    return value


def rule_ids(text: str, profile: str = "strict", **updates: Any) -> set[str]:
    return {item["rule_id"] for item in collect_diagnostics(text, profile, glossary(**updates))}


def test_sentence_splitting_preserves_lines_and_ignores_nonprose() -> None:
    text = """---
title: ignored
---
# Procedure

Install the package.
Restart the
service.

```bash
delete --all
```
| API | value |
| --- | --- |
"""
    sentences = parse_markdown(text, {"install", "restart"})
    assert [(item.text, item.line) for item in sentences] == [
        ("Install the package.", 6),
        ("Restart the service.", 7),
    ]


def test_all_language_rules_are_detected() -> None:
    cases: dict[str, tuple[str, dict[str, Any]]] = {
        "MTE-SENT-001": ("Install the package and restart the service.", {}),
        "MTE-TERM-001": (
            "Run the daemon.",
            {"terms": [{"preferred": "service", "forbidden": ["daemon"]}]},
        ),
        "MTE-VOICE-001": ("The operator is notified.", {}),
        "MTE-REF-001": ("Restart it.", {}),
        "MTE-PHRASAL-001": ("Set up the service.", {}),
        "MTE-COND-001": ("Restart the service if the check fails.", {}),
        "MTE-WARN-001": ("Delete the file.", {}),
        "MTE-ABBR-001": ("Use the API.", {}),
        "MTE-NOM-001": ("Configuration management is necessary.", {}),
        "MTE-LEN-001": (" ".join(["Information"] * 26) + ".", {}),
    }
    for expected, (text, updates) in cases.items():
        assert expected in rule_ids(text, **updates), expected


def test_warning_and_abbreviation_definitions_prevent_findings() -> None:
    text = """# Removal

WARNING: The file cannot be recovered.

Delete the file.

Application programming interface (API) access is available.
"""
    ids = rule_ids(text)
    assert "MTE-WARN-001" not in ids
    assert "MTE-ABBR-001" not in ids


def test_standard_profile_downgrades_only_style_rules() -> None:
    diagnostics = collect_diagnostics(
        "The service is configured. Set up the API. Restart it.",
        "standard",
        glossary(abbreviations={"API": "application programming interface"}),
    )
    severity = {item["rule_id"]: item["severity"] for item in diagnostics}
    assert severity["MTE-VOICE-001"] == "warning"
    assert severity["MTE-PHRASAL-001"] == "warning"
    assert severity["MTE-REF-001"] == "error"
    assert "MTE-LEN-001" not in severity


def test_language_cli_json_and_exit_codes(tmp_path: Path) -> None:
    glossary_path = tmp_path / "glossary.json"
    manual = tmp_path / "manual.md"
    glossary_path.write_text(json.dumps(glossary()), encoding="utf-8")
    manual.write_text("Install the package and restart the service.\n", encoding="utf-8")
    command = [
        sys.executable,
        str(SCRIPT),
        "--profile",
        "strict",
        "--glossary",
        str(glossary_path),
        str(manual),
    ]
    first = subprocess.run(command, capture_output=True, text=True, check=False)
    second = subprocess.run(command, capture_output=True, text=True, check=False)
    assert first.returncode == 1
    assert first.stdout == second.stdout
    assert json.loads(first.stdout)["violations"][0]["line"] == 1

    glossary_path.write_text("{}", encoding="utf-8")
    valid = subprocess.run(command, capture_output=True, text=True, check=False)
    assert valid.returncode == 1

    glossary_path.write_text("[]", encoding="utf-8")
    invalid = subprocess.run(command, capture_output=True, text=True, check=False)
    assert invalid.returncode == 2
    assert "error" in json.loads(invalid.stdout)
