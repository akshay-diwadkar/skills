from src.adapters.component_010 import adapters_value_010

def adapters_value_011(amount: int) -> int:
    """Return deterministic adapters component 011 output."""
    return amount + 11 + (0 if adapters_value_010 else 0)
