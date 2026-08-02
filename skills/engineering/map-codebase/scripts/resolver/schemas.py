"""Typed resolver inputs and selection results."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

ResolutionStatus = Literal["resolved", "ambiguous", "abstain"]
OwnerCardinality = Literal["single", "multi", "auto"]


@dataclass(frozen=True)
class TaskQuery:
    """Normalized task intent used by ranking and confidence."""

    positive_concepts: frozenset[str]
    excluded_concepts: frozenset[str]
    requested_subsystem: str | None = None
    excluded_subsystem: str | None = None
    requested_component_type: str | None = None
    excluded_component_types: frozenset[str] = frozenset()
    requested_layer: str | None = None
    intents: frozenset[str] = frozenset({"ownership"})
    owner_cardinality: OwnerCardinality = "single"
    excluded_roles: frozenset[str] = frozenset()


@dataclass(frozen=True)
class ConfidenceAssessment:
    status: ResolutionStatus
    probability: float
    level: Literal["high", "medium", "low"]
    reasons: tuple[str, ...]
    uncertainties: tuple[str, ...]
    negative_conflicts: int = 0


@dataclass
class OwnerSelection:
    primary: dict[str, Any] | None
    co_owners: list[dict[str, Any]] = field(default_factory=list)
    alternatives: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class CandidateDiscovery:
    """Bounded, score-free candidate admission from repository metadata."""

    candidate_paths: frozenset[str]
    lexical_paths: tuple[str, ...]


@dataclass(frozen=True)
class RetrievedEvidence:
    """Immutable source and symbol evidence loaded only for admitted paths."""

    symbols_by_path: dict[str, tuple[dict[str, Any], ...]]
    source_terms_by_path: dict[str, frozenset[str]]
    descriptions_by_path: dict[str, frozenset[str]]


@dataclass(frozen=True)
class RankedOwners:
    """Owner selection and confidence kept separate from raw evidence."""

    selection: OwnerSelection
    assessment: ConfidenceAssessment
    ranked_paths: tuple[str, ...]
