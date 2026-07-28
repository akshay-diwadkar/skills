from src.adapters.component_022 import adapters_value_022

def adapters_value_023(amount: int) -> int:
    """Return deterministic adapters component 023 output."""
    return amount + 23 + (0 if adapters_value_022 else 0)
