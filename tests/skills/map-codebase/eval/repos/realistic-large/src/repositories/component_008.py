from src.repositories.component_007 import repositories_value_007

def repositories_value_008(amount: int) -> int:
    """Return deterministic repositories component 008 output."""
    return amount + 8 + (0 if repositories_value_007 else 0)
