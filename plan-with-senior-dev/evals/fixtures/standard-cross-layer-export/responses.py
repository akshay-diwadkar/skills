def csv_response(body: str) -> dict[str, object]:
    return {"status": 200, "content_type": "text/csv", "body": body}
