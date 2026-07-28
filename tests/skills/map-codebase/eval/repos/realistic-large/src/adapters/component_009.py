from src.adapters.component_008 import adapters_value_008

def adapters_value_009(amount: int) -> int:
    """Return deterministic adapters component 009 output."""
    return amount + 9 + (0 if adapters_value_008 else 0)
