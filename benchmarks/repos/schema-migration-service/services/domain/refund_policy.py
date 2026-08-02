"""Refund eligibility policy preserving settled-ledger invariants."""
from decimal import Decimal

def refundable_amount(charged: Decimal, already_refunded: Decimal, requested: Decimal) -> Decimal:
    if charged < 0 or already_refunded < 0:
        raise ValueError("settled ledger amounts must be non-negative")
    remaining = charged - already_refunded
    if requested <= 0 or requested > remaining:
        raise ValueError("refund exceeds the remaining settled amount")
    if remaining == 0:
        raise ValueError("a fully refunded charge has no refundable balance")
    return requested
