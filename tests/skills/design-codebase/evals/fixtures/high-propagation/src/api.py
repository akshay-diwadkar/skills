def status_payload(order: dict) -> dict:
    return {"status": order["internal_status"]}
