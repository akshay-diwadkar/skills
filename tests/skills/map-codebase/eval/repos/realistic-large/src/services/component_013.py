from src.services.component_012 import services_value_012

def services_value_013(amount: int) -> int:
    """Return deterministic services component 013 output."""
    return amount + 13 + (0 if services_value_012 else 0)
