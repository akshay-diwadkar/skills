from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILL_DIR = ROOT / "skills" / "engineering" / "map-codebase"
SKILL_MD = SKILL_DIR / "SKILL.md"
REFERENCES_DIR = SKILL_DIR / "references"
DESCRIPTION_CASES = ROOT / "tests" / "skills" / "map-codebase" / "eval" / "description-cases.json"


def _normalised_bullets(text: str) -> set[str]:
    return {
        re.sub(r"\s+", " ", line[2:].strip()).casefold()
        for line in text.splitlines()
        if line.startswith("- ")
    }


def test_every_reference_is_linked_directly_from_skill() -> None:
    skill = SKILL_MD.read_text(encoding="utf-8")
    linked = set(re.findall(r"\]\(references/([^)#]+\.md)(?:#[^)]+)?\)", skill))
    expected = {path.name for path in REFERENCES_DIR.glob("*.md")}

    assert linked == expected


def test_skill_and_references_do_not_duplicate_bullets() -> None:
    skill_bullets = _normalised_bullets(SKILL_MD.read_text(encoding="utf-8"))
    for reference in REFERENCES_DIR.glob("*.md"):
        duplicate = skill_bullets & _normalised_bullets(reference.read_text(encoding="utf-8"))
        assert duplicate == set(), reference.name


def test_untracked_default_and_opt_out_are_both_explicit() -> None:
    skill = SKILL_MD.read_text(encoding="utf-8")
    contract = (REFERENCES_DIR / "knowledge-contract.md").read_text(encoding="utf-8")

    assert "untracked files are included by default" in skill
    assert "`include_untracked = false`" in skill
    assert "untracked files by default" in contract
    assert "`include_untracked = false`" in contract


def test_description_eval_corpus_is_balanced() -> None:
    cases = json.loads(DESCRIPTION_CASES.read_text(encoding="utf-8"))

    assert len(cases) == 20
    assert len({case["id"] for case in cases}) == 20
    assert Counter((case["split"], case["should_trigger"]) for case in cases) == {
        ("tuning", True): 5,
        ("tuning", False): 5,
        ("heldout", True): 5,
        ("heldout", False): 5,
    }
    assert all(set(case) == {"id", "split", "should_trigger", "prompt"} for case in cases)
