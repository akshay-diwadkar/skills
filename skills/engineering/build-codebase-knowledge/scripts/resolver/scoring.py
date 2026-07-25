"""Stage C & D: Candidate generation and weighted multi-evidence scoring."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def score_candidates(
    signals: dict[str, Any],
    intents: list[str],
    index_data: dict[str, Any],
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    """Score candidate files based on multi-signal matching and graph proximity."""
    weights = config.get("weights", {})
    w_exact_path = weights.get("exact_path", 10.0)
    w_exact_sym = weights.get("exact_symbol", 10.0)
    w_filename = weights.get("filename", 7.0)
    w_subsystem = weights.get("subsystem", 5.0)
    w_entry = weights.get("entry_point", 5.0)
    w_test = weights.get("related_test", 4.0)
    w_config = weights.get("configuration", 4.0)
    p_gen = weights.get("generated_penalty", -8.0)
    p_vendor = weights.get("vendor_penalty", -10.0)

    files = index_data.get("files", [])
    entry_points = {ep["path"] for ep in index_data.get("entry_points", [])}
    generated_paths = set(index_data.get("generated_paths", []))
    candidates: list[dict[str, Any]] = []

    raw_idents = set(signals.get("raw_identifiers", []))
    split_words = set(signals.get("split_words", []))
    paths_in_task = set(signals.get("paths", []))

    for f in files:
        path = f["path"]
        raw_score = 0.0
        reasons: list[str] = []
        matched_symbols: set[str] = set()

        # 1. Exact path match
        for task_path in paths_in_task:
            if task_path in path or path.endswith(task_path):
                raw_score += w_exact_path
                reasons.append(f"exact path match: {task_path}")

        # 2. Symbol match
        for sym in f.get("symbols", []):
            if sym.lower() in [i.lower() for i in raw_idents]:
                raw_score += w_exact_sym
                matched_symbols.add(sym)
                reasons.append(f"exact symbol match: {sym}")

        # 3. Filename stem match
        stem = Path(path).stem.lower()
        for word in split_words:
            if len(word) > 2 and word in stem:
                raw_score += w_filename
                reasons.append(f"filename match: {word}")

        # 4. Subsystem match
        subsystem = f.get("subsystem", "").lower()
        if subsystem in signals.get("subsystems", []):
            raw_score += w_subsystem
            reasons.append(f"subsystem match: {subsystem}")

        # 5. Entry point proximity
        if path in entry_points:
            raw_score += w_entry
            reasons.append("entry point proximity")

        # 6. Intent match
        if "test" in intents and f.get("role") == "test":
            raw_score += w_test
            reasons.append("test intent match")
        if "configuration" in intents and f.get("role") == "configuration":
            raw_score += w_config
            reasons.append("config intent match")

        # Penalties
        if path in generated_paths:
            raw_score += p_gen
            reasons.append("penalty: generated code")
        if "vendor" in path.lower() or "node_modules" in path.lower():
            raw_score += p_vendor
            reasons.append("penalty: vendor code")

        if raw_score > 0:
            exact_count = sum(1 for r in reasons if "exact" in r)
            norm_score = min(round(raw_score / 25.0, 2), 1.0)

            candidates.append({
                "path": path,
                "role": f.get("role", "source"),
                "subsystem": f.get("subsystem", "root"),
                "score": norm_score,
                "raw_score": raw_score,
                "exact_count": exact_count,
                "depth": path.count("/"),
                "reasons": sorted(list(set(reasons))),
                "symbols": sorted(list(matched_symbols)),
                "imports": f.get("imports", []),
                "imported_by": f.get("imported_by", []),
                "tests": f.get("tests", []),
            })

    # Deterministic multi-key tie-breaking
    # 1. raw_score (desc)
    # 2. exact_count (desc)
    # 3. depth (asc - shallower paths preferred)
    # 4. path (asc lexical order)
    sorted_candidates = sorted(
        candidates,
        key=lambda c: (-c["raw_score"], -c["exact_count"], c["depth"], c["path"]),
    )

    return sorted_candidates
