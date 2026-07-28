from src.adapters.component_011 import adapters_value_011

def adapters_value_012(amount: int) -> int:
    """Return deterministic adapters component 012 output."""
    return amount + 12 + (0 if adapters_value_011 else 0)
