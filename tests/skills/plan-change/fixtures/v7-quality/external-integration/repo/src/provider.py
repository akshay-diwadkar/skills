def charge_request(amount: int, idempotency_key: str) -> str:
    return f"charged:{amount}:{idempotency_key}"
