"""Retrieval benchmark metrics calculator."""

from __future__ import annotations

import math


def estimate_tokens(text: str) -> int:
    """Deterministic token estimator (~4 chars per token)."""
    return max(1, len(text) // 4)


def compute_mrr(retrieved: list[str], targets: list[str]) -> float:
    """Compute Mean Reciprocal Rank."""
    for idx, path in enumerate(retrieved, start=1):
        if path in targets:
            return round(1.0 / idx, 4)
    return 0.0


def compute_recall_at_k(retrieved: list[str], targets: list[str], k: int) -> float:
    """Compute Recall@k."""
    if not targets:
        return 1.0
    slice_k = retrieved[:k]
    hits = sum(1 for t in targets if t in slice_k)
    return round(hits / len(targets), 4)


def compute_precision_at_k(retrieved: list[str], targets: list[str], k: int) -> float:
    """Compute Precision@k."""
    slice_k = retrieved[:k]
    if not slice_k:
        return 0.0
    hits = sum(1 for item in slice_k if item in targets)
    return round(hits / len(slice_k), 4)


def compute_ndcg_at_k(retrieved: list[str], targets: list[str], k: int) -> float:
    """Compute Normalized Discounted Cumulative Gain at k (nDCG@k)."""
    if not targets:
        return 1.0

    dcg = 0.0
    for idx, item in enumerate(retrieved[:k], start=1):
        rel = 1.0 if item in targets else 0.0
        dcg += rel / math.log2(idx + 1)

    idcg = sum(1.0 / math.log2(idx + 1) for idx in range(1, min(len(targets), k) + 1))
    return round(dcg / max(idcg, 1.0e-9), 4)
