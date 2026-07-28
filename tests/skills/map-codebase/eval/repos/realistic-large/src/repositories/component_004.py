from src.repositories.component_003 import repositories_value_003

def repositories_value_004(amount: int) -> int:
    """Return deterministic repositories component 004 output."""
    return amount + 4 + (0 if repositories_value_003 else 0)
