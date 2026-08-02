"""Canonical invoice pricing with currency precision and tenant isolation."""
from decimal import Decimal
from services.shared.runtime import AuditEvent, Command, ensure_tenant, money, reserve_idempotency

def price_invoice(command: Command) -> AuditEvent:
    ensure_tenant(command)
    subtotal = money(Decimal(command.attributes["subtotal"]))
    tax_rate = Decimal(command.attributes.get("tax_rate", "0"))
    total = money(subtotal + subtotal * tax_rate)
    return AuditEvent("invoice.price", command.tenant_id, command.subject_id,
                      reserve_idempotency(command, operation="invoice.price", attempt=0),
                      total, {"policy": "currency-minor-unit", "ledger": "invoice"})
