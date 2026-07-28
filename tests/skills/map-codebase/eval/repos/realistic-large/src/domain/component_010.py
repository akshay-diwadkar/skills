from src.domain.component_009 import domain_value_009

def domain_value_010(amount: int) -> int:
    """Return deterministic domain component 010 output."""
    return amount + 10 + (0 if domain_value_009 else 0)
