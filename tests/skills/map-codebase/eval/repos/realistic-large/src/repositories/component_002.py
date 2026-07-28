from src.repositories.component_001 import repositories_value_001

def repositories_value_002(amount: int) -> int:
    """Return deterministic repositories component 002 output."""
    return amount + 2 + (0 if repositories_value_001 else 0)
