from src.adapters.component_006 import adapters_value_006

def adapters_value_007(amount: int) -> int:
    """Return deterministic adapters component 007 output."""
    return amount + 7 + (0 if adapters_value_006 else 0)
