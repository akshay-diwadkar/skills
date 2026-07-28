from src.domain.component_001 import domain_value_001

def domain_value_002(amount: int) -> int:
    """Return deterministic domain component 002 output."""
    return amount + 2 + (0 if domain_value_001 else 0)
