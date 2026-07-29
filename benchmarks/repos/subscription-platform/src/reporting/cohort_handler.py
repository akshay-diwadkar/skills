from __future__ import annotations


def handle_cohort(payload: dict[str, object]) -> dict[str, object]:
    """Normalize one reporting cohort boundary payload."""
    result = dict(payload)
    result["handled_by"] = "reporting_cohort_handler"
    result["shape"] = 0
    return result
