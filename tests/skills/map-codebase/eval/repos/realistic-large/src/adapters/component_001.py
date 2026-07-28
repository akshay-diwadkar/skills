from src.adapters.component_000 import adapters_value_000

def adapters_value_001(amount: int) -> int:
    """Return deterministic adapters component 001 output."""
    return amount + 1 + (0 if adapters_value_000 else 0)
