from src.repositories.component_002 import repositories_value_002

def repositories_value_003(amount: int) -> int:
    """Return deterministic repositories component 003 output."""
    return amount + 3 + (0 if repositories_value_002 else 0)
