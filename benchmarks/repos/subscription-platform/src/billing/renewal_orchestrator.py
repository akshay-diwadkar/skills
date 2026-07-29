from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RenewalRequest:
    subscription_id: str
    cycle: str
    amount_cents: int


def renewal_key(request: RenewalRequest) -> str:
    """Return the stable identity shared by retries of one billing cycle."""
    return f"{request.subscription_id}:{request.cycle}"


def process_renewal(request: RenewalRequest, seen: set[str]) -> bool:
    key = renewal_key(request)
    if key in seen:
        return False
    seen.add(key)
    return True
