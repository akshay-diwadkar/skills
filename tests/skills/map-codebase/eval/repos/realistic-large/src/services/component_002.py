from src.services.component_001 import services_value_001

def services_value_002(amount: int) -> int:
    """Return deterministic services component 002 output."""
    return amount + 2 + (0 if services_value_001 else 0)
