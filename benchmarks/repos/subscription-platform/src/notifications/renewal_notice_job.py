from __future__ import annotations


def renewal_notice(subscription_id: str, successful: bool) -> dict[str, str]:
    state = "renewed" if successful else "needs-attention"
    return {"subscription_id": subscription_id, "state": state}
