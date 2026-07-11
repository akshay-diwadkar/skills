REPORTS = {("t1", "r1"): {"status": "completed", "rows": [["a", 1]]}}


def get_report(report_id: str, tenant_id: str) -> dict[str, object]:
    return REPORTS[(tenant_id, report_id)]
