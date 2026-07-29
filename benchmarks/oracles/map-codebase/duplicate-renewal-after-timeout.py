from src.billing.renewal_orchestrator import RenewalRequest, process_renewal

request = RenewalRequest("sub-7", "2026-07", 2500)
seen: set[str] = set()
assert process_renewal(request, seen)
assert not process_renewal(request, seen)
