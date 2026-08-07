"""Shared utilities for test system baseline tools.

Holds timing bucket definitions, table-driven path-to-layer resolution,
and TypedDict structures shared between build_test_baseline and
test_baseline_recorder.
"""

from __future__ import annotations

from typing import Sequence, TypedDict

BUCKET_EDGES = (0.0, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0)
BUCKET_LABELS = tuple(f"{edge:g}s" for edge in BUCKET_EDGES)

FIXTURE_PATH_MARKERS = (
    "/evals/",
    "/eval/",
    "/fixtures/",
    "/repos/",
    "/worked-example-fixtures",
    "/static-regression-cases",
)

# Table-driven prefix mapping to eliminate repeated switch cascades
PATH_LAYER_MAP: list[tuple[str, str]] = [
    ("tests/skills/", "skill-local"),
    ("skills/", "skill-local"),
    ("tests/repository/", "repository-policy"),
    ("repository/", "repository-policy"),
    ("tests/shared/", "shared-runtime"),
    ("shared/", "shared-runtime"),
    ("tests/skill_protocol/", "shared-protocol"),
    ("skill_protocol/", "shared-protocol"),
    ("tests/classification/", "classification"),
    ("classification/", "classification"),
    ("tests/integration/", "installed-execution"),
    ("integration/", "installed-execution"),
    ("tests/benchmarks/", "benchmark-fixture"),
    ("benchmarks/", "benchmark-fixture"),
]


class NodeMetrics(TypedDict):
    """Runtime metrics tracked per test node."""

    bucket: str
    subprocess: int
    copy_bytes: int
    copy_count: int


def bucket_seconds(seconds: float) -> str:
    """Return the bucket label for a given duration in seconds."""
    for index, edge in enumerate(BUCKET_EDGES):
        if seconds < edge:
            return BUCKET_LABELS[max(index - 1, 0)]
    return f">{BUCKET_EDGES[-1]:g}s"


def bucket_index(label: str) -> int:
    """Return the ordinal index of a bucket label for median calculations."""
    try:
        return BUCKET_LABELS.index(label)
    except ValueError:
        return len(BUCKET_LABELS) - 1


def median_bucket(labels: Sequence[str]) -> str:
    """Compute the median duration bucket label from a collection of labels."""
    if not labels:
        return BUCKET_LABELS[0]
    indices = sorted(bucket_index(label) for label in labels)
    return BUCKET_LABELS[indices[(len(indices) - 1) // 2]]


def derive_layer_from_path(relative_path: str) -> str:
    """Derive test layer from a relative file path using table-driven prefix matching."""
    lowered = relative_path.replace("\\", "/").lower()
    if lowered.startswith("skills") and any(m in lowered for m in FIXTURE_PATH_MARKERS):
        return "fixture-repository"
    for prefix, layer in PATH_LAYER_MAP:
        if lowered.startswith(prefix) or f"/{prefix}" in lowered:
            return layer
    return "repository-policy"
