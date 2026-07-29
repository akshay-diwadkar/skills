from __future__ import annotations


class AmbiguousGatewayTimeout(RuntimeError):
    """The provider may have accepted a request before the response timed out."""


def charge(idempotency_key: str, amount_cents: int) -> dict[str, object]:
    if not idempotency_key:
        raise ValueError("idempotency key is required")
    return {"key": idempotency_key, "amount_cents": amount_cents, "accepted": True}
