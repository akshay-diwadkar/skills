from src import provider

def charge(amount: int, idempotency_key: str) -> str:
    return provider.charge_request(amount, idempotency_key)
