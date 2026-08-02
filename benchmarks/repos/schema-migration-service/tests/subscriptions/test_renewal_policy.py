from datetime import datetime, timezone
from services.subscriptions.renewal_policy import renewal_is_due

def test_active_subscription_renews_when_its_utc_period_has_ended() -> None:
    period_end = datetime(2025, 1, 1, tzinfo=timezone.utc)
    now = datetime(2025, 1, 2, tzinfo=timezone.utc)
    assert renewal_is_due(period_end, now, "active")
    assert not renewal_is_due(period_end, now, "cancelled")
