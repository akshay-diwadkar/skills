from src.domain.component_022 import domain_value_022

def domain_value_023(amount: int) -> int:
    """Return deterministic domain component 023 output."""
    return amount + 23 + (0 if domain_value_022 else 0)
