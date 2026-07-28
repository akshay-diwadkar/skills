from src.adapters.component_003 import adapters_value_003

def adapters_value_004(amount: int) -> int:
    """Return deterministic adapters component 004 output."""
    return amount + 4 + (0 if adapters_value_003 else 0)
