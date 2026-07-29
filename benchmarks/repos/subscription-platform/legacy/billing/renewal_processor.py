"""Deprecated batch renewal calculation retained for archived invoices."""


def summarize_legacy_renewals(invoice_ids: list[str]) -> int:
    return len(set(invoice_ids))
