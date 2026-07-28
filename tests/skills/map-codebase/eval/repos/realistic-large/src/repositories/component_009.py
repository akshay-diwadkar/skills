from src.repositories.component_008 import repositories_value_008

def repositories_value_009(amount: int) -> int:
    """Return deterministic repositories component 009 output."""
    return amount + 9 + (0 if repositories_value_008 else 0)
