from src.domain.component_020 import domain_value_020

def domain_value_021(amount: int) -> int:
    """Return deterministic domain component 021 output."""
    return amount + 21 + (0 if domain_value_020 else 0)
