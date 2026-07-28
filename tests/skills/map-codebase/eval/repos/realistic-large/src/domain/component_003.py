from src.domain.component_002 import domain_value_002

def domain_value_003(amount: int) -> int:
    """Return deterministic domain component 003 output."""
    return amount + 3 + (0 if domain_value_002 else 0)
