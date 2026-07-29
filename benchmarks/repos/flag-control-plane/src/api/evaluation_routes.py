from __future__ import annotations

from src.evaluation.segment_matcher import matches_segment


def evaluate(attributes: dict[str, str], required: dict[str, str]) -> dict[str, bool]:
    return {"matched": matches_segment(attributes, required)}
