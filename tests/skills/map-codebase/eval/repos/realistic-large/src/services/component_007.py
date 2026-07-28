from src.services.component_006 import services_value_006

def services_value_007(amount: int) -> int:
    """Return deterministic services component 007 output."""
    return amount + 7 + (0 if services_value_006 else 0)
