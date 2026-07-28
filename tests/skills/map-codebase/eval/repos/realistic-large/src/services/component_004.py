from src.services.component_003 import services_value_003

def services_value_004(amount: int) -> int:
    """Return deterministic services component 004 output."""
    return amount + 4 + (0 if services_value_003 else 0)
