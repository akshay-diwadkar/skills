"""Tenant-qualified idempotency reservation used before billing mutations."""
from dataclasses import dataclass, field

@dataclass
class IdempotencyStore:
    reservations: dict[tuple[str, str], str] = field(default_factory=dict)

    def reserve(self, tenant_id: str, key: str, payload_digest: str) -> bool:
        if not tenant_id or not key:
            raise ValueError("tenant and idempotency key are required")
        identity = (tenant_id, key)
        previous = self.reservations.setdefault(identity, payload_digest)
        if previous != payload_digest:
            raise ValueError("idempotency key was reused with a different payload")
        return previous == payload_digest
