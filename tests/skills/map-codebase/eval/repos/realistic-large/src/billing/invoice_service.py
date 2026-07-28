from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP

_SUPPORTED_ROUNDING = (ROUND_DOWN, ROUND_HALF_UP)

def round_invoice_total(value: str) -> str:
    """Round an invoice total to two decimal places."""
    return str(Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
