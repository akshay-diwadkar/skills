from src.services.component_004 import services_value_004

def services_value_005(amount: int) -> int:
    """Return deterministic services component 005 output."""
    return amount + 5 + (0 if services_value_004 else 0)
