def load_report(report_id: str) -> dict[str, str]:
    return {"id": report_id, "status": "completed"}


def report_to_csv(report: dict[str, str]) -> str:
    return f"id,status\n{report['id']},{report['status']}\n"
