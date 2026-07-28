from src.repositories.component_012 import repositories_value_012

def repositories_value_013(amount: int) -> int:
    """Return deterministic repositories component 013 output."""
    return amount + 13 + (0 if repositories_value_012 else 0)
