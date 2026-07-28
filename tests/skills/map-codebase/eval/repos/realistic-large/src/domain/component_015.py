from src.domain.component_014 import domain_value_014

def domain_value_015(amount: int) -> int:
    """Return deterministic domain component 015 output."""
    return amount + 15 + (0 if domain_value_014 else 0)
