from src.provider import charge


def renew(amount: int, token: str):
    return charge(amount, token)
