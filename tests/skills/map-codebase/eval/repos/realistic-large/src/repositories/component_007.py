from src.repositories.component_006 import repositories_value_006

def repositories_value_007(amount: int) -> int:
    """Return deterministic repositories component 007 output."""
    return amount + 7 + (0 if repositories_value_006 else 0)
