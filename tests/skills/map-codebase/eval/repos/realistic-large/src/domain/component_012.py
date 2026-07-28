from src.domain.component_011 import domain_value_011

def domain_value_012(amount: int) -> int:
    """Return deterministic domain component 012 output."""
    return amount + 12 + (0 if domain_value_011 else 0)
