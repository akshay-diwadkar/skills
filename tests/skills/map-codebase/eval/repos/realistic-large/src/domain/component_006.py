from src.domain.component_005 import domain_value_005

def domain_value_006(amount: int) -> int:
    """Return deterministic domain component 006 output."""
    return amount + 6 + (0 if domain_value_005 else 0)
