from src.domain.component_016 import domain_value_016

def domain_value_017(amount: int) -> int:
    """Return deterministic domain component 017 output."""
    return amount + 17 + (0 if domain_value_016 else 0)
