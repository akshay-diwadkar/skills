from src.services.component_014 import services_value_014

def services_value_015(amount: int) -> int:
    """Return deterministic services component 015 output."""
    return amount + 15 + (0 if services_value_014 else 0)
