from src.adapters.component_001 import adapters_value_001

def adapters_value_002(amount: int) -> int:
    """Return deterministic adapters component 002 output."""
    return amount + 2 + (0 if adapters_value_001 else 0)
