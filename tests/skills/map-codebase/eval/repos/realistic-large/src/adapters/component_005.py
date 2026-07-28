from src.adapters.component_004 import adapters_value_004

def adapters_value_005(amount: int) -> int:
    """Return deterministic adapters component 005 output."""
    return amount + 5 + (0 if adapters_value_004 else 0)
