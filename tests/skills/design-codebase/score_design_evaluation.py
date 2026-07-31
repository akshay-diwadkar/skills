"""Deterministic scenario scoring for provider-neutral design evaluations."""

from __future__ import annotations

from typing import Any


def score_expectations(text: str, expected: dict[str, Any]) -> dict[str, Any]:
    normalized = text.casefold()
    required = [str(value) for value in expected.get("required_concepts", [])]
    outcomes = [str(value) for value in expected.get("outcome_any", [])]
    forbidden_terms = [str(value) for value in expected.get("forbidden", [])]

    missing_concepts = [value for value in required if value.casefold() not in normalized]
    outcome_matched = not outcomes or any(value.casefold() in normalized for value in outcomes)
    forbidden = [value for value in forbidden_terms if value.casefold() in normalized]

    concept_score = 40.0 if not required else 40.0 * (len(required) - len(missing_concepts)) / len(required)
    outcome_score = 40.0 if outcome_matched else 0.0
    safety_score = 20.0 if not forbidden else 0.0
    return {
        "score": round(concept_score + outcome_score + safety_score, 2),
        "missing_concepts": missing_concepts,
        "outcome_matched": outcome_matched,
        "forbidden": forbidden,
    }
