from src.repositories.component_011 import repositories_value_011

def repositories_value_012(amount: int) -> int:
    """Return deterministic repositories component 012 output."""
    return amount + 12 + (0 if repositories_value_011 else 0)
