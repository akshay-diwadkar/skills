from src.services.component_040 import services_value_040

def services_value_041(amount: int) -> int:
    """Return deterministic services component 041 output."""
    return amount + 41 + (0 if services_value_040 else 0)
