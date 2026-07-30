"""Phase 1 façade for ranking and adaptive owner selection."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from resolver.aggregation import select_owners
from resolver.confidence import assess_confidence
from resolver.schemas import ConfidenceAssessment, OwnerSelection, TaskQuery


def resolve_phase1(
    ranked: list[dict[str, Any]],
    targets: list[dict[str, Any]],
    query: TaskQuery,
    *,
    freshness: str,
    focused: bool,
    underspecified: bool,
) -> tuple[OwnerSelection, ConfidenceAssessment]:
    confidence = assess_confidence(
        ranked,
        freshness=freshness,
        focused=focused,
        underspecified=underspecified,
    )
    owners = select_owners(ranked, targets, query, abstain=confidence.status == "abstain")
    if (
        query.owner_cardinality == "multi"
        and owners.primary is not None
        and owners.co_owners
        and confidence.status == "ambiguous"
        and confidence.negative_conflicts == 0
    ):
        confidence = replace(
            confidence,
            status="resolved",
            probability=max(confidence.probability, 0.72),
            reasons=(*confidence.reasons, "explicit multi-owner request has independent owner evidence"),
        )
    return owners, confidence
