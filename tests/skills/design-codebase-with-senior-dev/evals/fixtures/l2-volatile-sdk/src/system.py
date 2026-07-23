def current(provider, amount: int) -> str:
    response = provider.authorize({"amount_cents": amount})
    return response["authorization_id"]


def refund(provider, authorization_id: str) -> bool:
    response = provider.refund({"authorization_id": authorization_id})
    return response["refunded"]
