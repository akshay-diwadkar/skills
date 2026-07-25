def json_response(report: dict[str, str]) -> tuple[str, str]:
    return "application/json", str(report)
