from services.api.billing_facade import settle_invoice
from services.persistence.idempotency_store import IdempotencyStore
from services.shared.runtime import Command

def test_settlement_prices_grants_and_publishes_as_one_application_flow() -> None:
    deliveries: list[tuple[str, str]] = []
    result = settle_invoice(
        Command("tenant-a", "invoice-a", {"subtotal": "10", "feature": "analytics"}),
        IdempotencyStore(),
        lambda tenant, event: deliveries.append((tenant, event)),
    )
    assert result.invoice.amount == 10
    assert result.grant.feature == "analytics"
    assert deliveries == [("tenant-a", "invoice-paid:invoice-a")]
