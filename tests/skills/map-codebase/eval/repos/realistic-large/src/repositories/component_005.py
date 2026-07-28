from src.repositories.component_004 import repositories_value_004

def repositories_value_005(amount: int) -> int:
    """Return deterministic repositories component 005 output."""
    return amount + 5 + (0 if repositories_value_004 else 0)
