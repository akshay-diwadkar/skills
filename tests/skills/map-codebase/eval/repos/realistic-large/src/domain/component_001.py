from src.domain.component_000 import domain_value_000

def domain_value_001(amount: int) -> int:
    """Return deterministic domain component 001 output."""
    return amount + 1 + (0 if domain_value_000 else 0)
