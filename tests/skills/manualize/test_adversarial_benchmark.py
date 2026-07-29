from __future__ import annotations

import json
from pathlib import Path

import pytest
from check_manual_language import collect_diagnostics

CASES = Path(__file__).parent / "evals" / "cases.json"
GLOSSARY = {
    "terms": [{"preferred": "service", "forbidden": ["daemon"]}],
    "abbreviations": {},
    "action_verbs": [],
    "phrasal_verbs": [],
    "hazardous_actions": [],
}


@pytest.mark.benchmark
def test_adversarial_language_corpus_is_exact_and_deterministic() -> None:
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    first = [
        sorted({item["rule_id"] for item in collect_diagnostics(case["text"], "strict", GLOSSARY)})
        for case in cases
    ]
    second = [
        sorted({item["rule_id"] for item in collect_diagnostics(case["text"], "strict", GLOSSARY)})
        for case in cases
    ]
    assert first == second
    for case, actual in zip(cases, first, strict=True):
        assert actual == case["expected"], case["id"]
