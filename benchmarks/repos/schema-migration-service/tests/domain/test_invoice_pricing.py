from decimal import Decimal
from services.domain.invoice_pricing import price_invoice
from services.shared.runtime import Command

def test_invoice_pricing_applies_minor_unit_rounding() -> None:
    event = price_invoice(Command("tenant-a", "invoice-a", {"subtotal": "10.005", "tax_rate": "0.20"}))
    assert event.amount == Decimal("12.01")
    assert event.metadata["policy"] == "currency-minor-unit"
