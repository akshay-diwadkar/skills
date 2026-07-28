from src.domain.component_006 import domain_value_006

def domain_value_007(amount: int) -> int:
    """Return deterministic domain component 007 output."""
    return amount + 7 + (0 if domain_value_006 else 0)
