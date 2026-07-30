"""General-purpose ranking math with bounded evidence."""

from __future__ import annotations

import math
from collections.abc import Iterable


def inverse_document_frequency(document_count: int, document_frequency: int) -> float:
    """Return stable BM25-style IDF without fixture-derived constants."""
    if document_count <= 0:
        return 0.0
    bounded = min(max(document_frequency, 0), document_count)
    return math.log(1.0 + (document_count - bounded + 0.5) / (bounded + 0.5))


def length_normalization(length: int, average_length: float) -> float:
    if length <= 0 or average_length <= 0:
        return 1.0
    return 1.0 / (0.25 + 0.75 * length / average_length)


def capped_sum(values: Iterable[float], cap: float) -> float:
    return min(sum(max(value, 0.0) for value in values), cap)


def conjunctive_match(dimensions: Iterable[bool]) -> float:
    matched = sum(bool(value) for value in dimensions)
    return 0.0 if matched < 2 else float((matched - 1) * 3)
