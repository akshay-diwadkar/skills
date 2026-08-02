"""Subscription renewal eligibility at the billing clock boundary."""
from datetime import datetime, timezone

def renewal_is_due(period_end: datetime, now: datetime, status: str) -> bool:
    if period_end.tzinfo is None or now.tzinfo is None:
        raise ValueError("renewal timestamps must be timezone-aware")
    if status not in {"active", "past_due"}:
        return False
    return period_end.astimezone(timezone.utc) <= now.astimezone(timezone.utc)
