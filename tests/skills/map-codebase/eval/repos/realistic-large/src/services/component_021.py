from src.services.component_020 import services_value_020

def services_value_021(amount: int) -> int:
    """Return deterministic services component 021 output."""
    return amount + 21 + (0 if services_value_020 else 0)
