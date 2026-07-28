from src.domain.component_008 import domain_value_008

def domain_value_009(amount: int) -> int:
    """Return deterministic domain component 009 output."""
    return amount + 9 + (0 if domain_value_008 else 0)
