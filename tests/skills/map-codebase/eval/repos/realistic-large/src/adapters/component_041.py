from src.adapters.component_040 import adapters_value_040

def adapters_value_041(amount: int) -> int:
    """Return deterministic adapters component 041 output."""
    return amount + 41 + (0 if adapters_value_040 else 0)
