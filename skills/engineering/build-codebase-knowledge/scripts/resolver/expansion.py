"""Stage F: Progressive graph-based candidate expansion engine."""

from __future__ import annotations

from typing import Any


def progressive_expand(
    candidates: list[dict[str, Any]],
    confidence: str,
    index_data: dict[str, Any],
    max_files_budget: int = 15,
) -> tuple[list[dict[str, Any]], str]:
    """Progressively expand target candidate set using graph imports, reverse imports, and tests."""
    selected_set: set[str] = set()
    expanded_candidates: list[dict[str, Any]] = []
    file_map = {f["path"]: f for f in index_data.get("files", [])}

    if not candidates:
        return [], "No candidates available for expansion."

    # Phase 1: High confidence primary candidates
    primary_candidates = candidates[:3] if confidence == "high" else candidates[:2]
    for cand in primary_candidates:
        if cand["path"] not in selected_set:
            selected_set.add(cand["path"])
            expanded_candidates.append(cand)

    # Phase 2: Direct tests and configs for primary candidates
    for cand in list(expanded_candidates):
        # Mapped test files
        for test_path in cand.get("tests", []):
            if test_path not in selected_set and len(expanded_candidates) < max_files_budget:
                selected_set.add(test_path)
                if test_path in file_map:
                    expanded_candidates.append(
                        {
                            "path": test_path,
                            "role": "test",
                            "subsystem": file_map[test_path].get("subsystem", "root"),
                            "score": 0.8,
                            "reasons": [f"direct test for {cand['path']}"],
                        }
                    )

    if confidence == "high":
        return expanded_candidates, "High confidence target slice satisfied."

    # Phase 3: Medium confidence 1st-order import and reverse import graph neighbors
    for cand in list(expanded_candidates):
        # Forward imports
        for imp in cand.get("imports", []):
            if imp not in selected_set and len(expanded_candidates) < max_files_budget:
                selected_set.add(imp)
                if imp in file_map:
                    expanded_candidates.append(
                        {
                            "path": imp,
                            "role": file_map[imp].get("role", "source"),
                            "subsystem": file_map[imp].get("subsystem", "root"),
                            "score": 0.6,
                            "reasons": [f"1st-order import of {cand['path']}"],
                        }
                    )

        # Reverse imports (imported_by)
        for rev_imp in cand.get("imported_by", []):
            if rev_imp not in selected_set and len(expanded_candidates) < max_files_budget:
                selected_set.add(rev_imp)
                if rev_imp in file_map:
                    expanded_candidates.append(
                        {
                            "path": rev_imp,
                            "role": file_map[rev_imp].get("role", "source"),
                            "subsystem": file_map[rev_imp].get("subsystem", "root"),
                            "score": 0.6,
                            "reasons": [f"1st-order reverse dependency of {cand['path']}"],
                        }
                    )

    if confidence == "medium":
        return expanded_candidates, "Medium confidence 1st-order graph expansion complete."

    # Phase 4: Low confidence subsystem expansion
    subsystems_to_expand = {cand.get("subsystem") for cand in expanded_candidates}
    for sub in subsystems_to_expand:
        for f in index_data.get("files", []):
            if f.get("subsystem") == sub and f["path"] not in selected_set:
                if len(expanded_candidates) < max_files_budget:
                    selected_set.add(f["path"])
                    expanded_candidates.append(
                        {
                            "path": f["path"],
                            "role": f.get("role", "source"),
                            "subsystem": sub,
                            "score": 0.4,
                            "reasons": [f"subsystem neighbor in {sub}"],
                        }
                    )

    return expanded_candidates, "Low confidence subsystem expansion complete."
