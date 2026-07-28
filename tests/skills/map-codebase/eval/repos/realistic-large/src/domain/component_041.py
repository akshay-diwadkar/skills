from src.domain.component_040 import domain_value_040

def domain_value_041(amount: int) -> int:
    """Return deterministic domain component 041 output."""
    return amount + 41 + (0 if domain_value_040 else 0)
