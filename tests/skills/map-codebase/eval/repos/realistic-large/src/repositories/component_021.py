from src.repositories.component_020 import repositories_value_020

def repositories_value_021(amount: int) -> int:
    """Return deterministic repositories component 021 output."""
    return amount + 21 + (0 if repositories_value_020 else 0)
