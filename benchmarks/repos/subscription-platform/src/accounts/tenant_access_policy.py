from __future__ import annotations


def may_manage_subscription(actor_tenant: str, subscription_tenant: str, role: str) -> bool:
    return actor_tenant == subscription_tenant and role in {"owner", "billing-admin"}
