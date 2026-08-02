"""Application boundary coordinating invoice settlement and entitlement delivery."""
from dataclasses import dataclass
from services.domain.invoice_pricing import price_invoice
from services.entitlements.grant_service import Grant, grant_paid_feature
from services.persistence.idempotency_store import IdempotencyStore
from services.shared.runtime import AuditEvent, Command
from services.workers.outbox_publisher import PendingEvent, publish_batch

@dataclass(frozen=True)
class SettlementResult:
    invoice: AuditEvent
    grant: Grant
    published_event_ids: tuple[str, ...]

def settle_invoice(command: Command, store: IdempotencyStore, publish) -> SettlementResult:
    """Price and settle one invoice while preserving the tenant idempotency boundary."""
    invoice = price_invoice(command)
    if not store.reserve(command.tenant_id, invoice.reservation, str(invoice.amount)):
        raise RuntimeError("invoice reservation could not be acquired")
    grant = grant_paid_feature(command.tenant_id, command.subject_id,
                               command.attributes["feature"], "paid", command.subject_id)
    published, quarantined = publish_batch(
        [PendingEvent(f"invoice-paid:{command.subject_id}", command.tenant_id, 0)], publish)
    if quarantined:
        raise RuntimeError("new invoice event was unexpectedly quarantined")
    return SettlementResult(invoice, grant, tuple(published))
