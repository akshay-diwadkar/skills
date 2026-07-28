from src.domain.component_012 import domain_value_012

def domain_value_013(amount: int) -> int:
    """Return deterministic domain component 013 output."""
    return amount + 13 + (0 if domain_value_012 else 0)
