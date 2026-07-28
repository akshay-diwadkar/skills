from src.adapters.component_012 import adapters_value_012

def adapters_value_013(amount: int) -> int:
    """Return deterministic adapters component 013 output."""
    return amount + 13 + (0 if adapters_value_012 else 0)
