from src.billing.invoice_service import round_invoice_total

assert round_invoice_total('10.125') == '10.13'
