from src.repositories.component_000 import repositories_value_000

def repositories_value_001(amount: int) -> int:
    """Return deterministic repositories component 001 output."""
    return amount + 1 + (0 if repositories_value_000 else 0)
