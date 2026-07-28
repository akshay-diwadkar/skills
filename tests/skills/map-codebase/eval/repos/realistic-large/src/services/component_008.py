from src.services.component_007 import services_value_007

def services_value_008(amount: int) -> int:
    """Return deterministic services component 008 output."""
    return amount + 8 + (0 if services_value_007 else 0)
