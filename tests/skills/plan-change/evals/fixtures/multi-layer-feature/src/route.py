from .responses import json_response
from .service import load_report


def get_report(report_id: str, accept: str) -> tuple[str, str]:
    report = load_report(report_id)
    return json_response(report)
