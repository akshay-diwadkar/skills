"""Grant entitlements only after the paid invoice event is committed."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Grant:
    tenant_id: str
    account_id: str
    feature: str
    source_invoice: str

def grant_paid_feature(tenant_id: str, account_id: str, feature: str, invoice_state: str, invoice_id: str) -> Grant:
    if invoice_state != "paid":
        raise ValueError("entitlements require a paid invoice")
    return Grant(tenant_id, account_id, feature, invoice_id)
