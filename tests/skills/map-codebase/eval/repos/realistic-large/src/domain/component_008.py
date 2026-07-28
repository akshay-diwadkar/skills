from src.domain.component_007 import domain_value_007

def domain_value_008(amount: int) -> int:
    """Return deterministic domain component 008 output."""
    return amount + 8 + (0 if domain_value_007 else 0)
