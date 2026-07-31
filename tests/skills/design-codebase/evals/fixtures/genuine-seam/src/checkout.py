from src.provider import charge


def checkout(amount: int, token: str):
    return charge(amount, token)
