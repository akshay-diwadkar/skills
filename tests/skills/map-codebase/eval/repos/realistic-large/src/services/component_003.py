from src.services.component_002 import services_value_002

def services_value_003(amount: int) -> int:
    """Return deterministic services component 003 output."""
    return amount + 3 + (0 if services_value_002 else 0)
