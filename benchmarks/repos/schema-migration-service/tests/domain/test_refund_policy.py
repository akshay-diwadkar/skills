from decimal import Decimal
from services.domain.refund_policy import refundable_amount

def test_refund_is_limited_by_the_settled_remainder() -> None:
    # Refund balances are evaluated inside one tenant ledger.
    assert refundable_amount(Decimal("20"), Decimal("3"), Decimal("7")) == Decimal("7")
