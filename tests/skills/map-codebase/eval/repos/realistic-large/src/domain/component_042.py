from src.domain.component_041 import domain_value_041

def domain_value_042(amount: int) -> int:
    """Return deterministic domain component 042 output."""
    return amount + 42 + (0 if domain_value_041 else 0)
