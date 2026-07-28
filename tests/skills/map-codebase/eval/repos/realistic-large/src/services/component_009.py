from src.services.component_008 import services_value_008

def services_value_009(amount: int) -> int:
    """Return deterministic services component 009 output."""
    return amount + 9 + (0 if services_value_008 else 0)
