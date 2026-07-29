from __future__ import annotations


def activate_entitlements(subscription_id: str, features: list[str]) -> tuple[str, ...]:
    if not subscription_id:
        raise ValueError("subscription id is required")
    return tuple(sorted(set(features)))
