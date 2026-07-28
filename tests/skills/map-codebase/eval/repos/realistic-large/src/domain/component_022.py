from src.domain.component_021 import domain_value_021

def domain_value_022(amount: int) -> int:
    """Return deterministic domain component 022 output."""
    return amount + 22 + (0 if domain_value_021 else 0)
