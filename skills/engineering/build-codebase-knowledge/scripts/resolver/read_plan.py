"""Stage G: Actionable read plan generation engine."""

from __future__ import annotations

from typing import Any


def generate_read_plan(
    expanded_candidates: list[dict[str, Any]],
    index_data: dict[str, Any],
) -> dict[str, Any]:
    """Generate an actionable, phase-structured read plan with dynamic repository skip list."""
    # Assign ordered read sequence
    read_sequence: list[dict[str, Any]] = []
    for idx, cand in enumerate(expanded_candidates, start=1):
        item = dict(cand)
        item["read_order"] = idx
        read_sequence.append(item)

    primary_files = [c["path"] for c in read_sequence if c.get("role") == "source"]
    test_files = [c["path"] for c in read_sequence if c.get("role") == "test"]
    config_files = [c["path"] for c in read_sequence if c.get("role") == "configuration"]

    phases = [
        {"phase": 1, "title": "Read primary implementation source modules", "files": primary_files[:3]},
        {"phase": 2, "title": "Verify contracts and direct test suites", "files": test_files[:2]},
        {"phase": 3, "title": "Check environment configuration manifests", "files": config_files[:2]},
        {
            "phase": 4,
            "title": "Source verification (verify actual logic in source before editing)",
            "files": primary_files,
        },
    ]

    # Dynamic skip list derived from repository ignored and generated paths
    ignored_paths = index_data.get("ignored_paths", [])
    generated_paths = index_data.get("generated_paths", [])

    dynamic_skip_list = sorted(
        list(set(ignored_paths[:10] + generated_paths[:5] + ["vendor/", "node_modules/", "dist/", ".git/"]))
    )

    return {
        "read_sequence": read_sequence,
        "phases": phases,
        "skip_list": dynamic_skip_list,
    }
