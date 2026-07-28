from src.domain.component_019 import domain_value_019

def domain_value_020(amount: int) -> int:
    """Return deterministic domain component 020 output."""
    return amount + 20 + (0 if domain_value_019 else 0)
