from src.domain.component_004 import domain_value_004

def domain_value_005(amount: int) -> int:
    """Return deterministic domain component 005 output."""
    return amount + 5 + (0 if domain_value_004 else 0)
