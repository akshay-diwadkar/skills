from src.adapters.component_020 import adapters_value_020

def adapters_value_021(amount: int) -> int:
    """Return deterministic adapters component 021 output."""
    return amount + 21 + (0 if adapters_value_020 else 0)
