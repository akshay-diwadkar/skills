"""Adaptive owner cardinality and alternative selection."""

from __future__ import annotations

from typing import Any

from resolver.schemas import OwnerSelection, TaskQuery


def select_owners(
    ranked: list[dict[str, Any]],
    targets: list[dict[str, Any]],
    query: TaskQuery,
    *,
    abstain: bool,
) -> OwnerSelection:
    by_path = {target["path"]: target for target in targets}
    ordered = [by_path[item["file"]["path"]] for item in ranked if item["file"]["path"] in by_path]
    if abstain or not ordered:
        return OwnerSelection(None, [], ordered[:2])
    primary = ordered[0]
    co_owners: list[dict[str, Any]] = []
    if query.owner_cardinality == "multi":
        top_score = float(ranked[0]["score"])
        covered = set(ranked[0].get("matched_concepts", set()))
        candidates = sorted(
            ranked[1:],
            key=lambda item: (
                -int(
                    bool(query.requested_component_type)
                    and not ranked[0].get("component_match", False)
                    and item.get("component_match", False)
                ),
                -len(set(item.get("matched_concepts", set())) - covered),
                -float(item.get("score", 0.0)),
                item["file"]["path"],
            ),
        )
        for item in candidates:
            if len(co_owners) >= 1:
                break
            novel = set(item.get("matched_concepts", set())) - covered
            if (
                item["file"]["path"] in by_path
                and item.get("direct_score", 0) >= max(8.0, top_score * 0.25)
                and item.get("negative_conflicts", 0) == 0
                and len(novel) >= 1
            ):
                co_owners.append(by_path[item["file"]["path"]])
                covered.update(item.get("matched_concepts", set()))
    selected = {primary["path"], *(owner["path"] for owner in co_owners)}
    alternatives = [target for target in ordered if target["path"] not in selected]
    alternative_limit = 2 if len(ranked) > 1 and float(ranked[0]["score"]) - float(ranked[1]["score"]) < 8 else 1
    return OwnerSelection(primary, co_owners, alternatives[:alternative_limit])
