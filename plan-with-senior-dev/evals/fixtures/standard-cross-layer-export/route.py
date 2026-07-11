from service import get_report


def download(report_id: str, tenant_id: str) -> dict[str, object]:
    report = get_report(report_id, tenant_id)
    if report["status"] != "completed":
        return {"status": 409}
    return {"status": 200, "body": report}
