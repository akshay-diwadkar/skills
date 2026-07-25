from . import gateway

charged: set[str] = set()


def charge_invoice(invoice_id: str, amount_cents: int) -> str:
    if invoice_id in charged:
        return "already-charged"
    receipt = gateway.charge(amount_cents)
    charged.add(invoice_id)
    return receipt
