from src.services.component_019 import services_value_019

def services_value_020(amount: int) -> int:
    """Return deterministic services component 020 output."""
    return amount + 20 + (0 if services_value_019 else 0)
