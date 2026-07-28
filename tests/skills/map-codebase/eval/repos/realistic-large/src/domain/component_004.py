from src.domain.component_003 import domain_value_003

def domain_value_004(amount: int) -> int:
    """Return deterministic domain component 004 output."""
    return amount + 4 + (0 if domain_value_003 else 0)
