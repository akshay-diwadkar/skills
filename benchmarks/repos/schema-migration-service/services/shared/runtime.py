from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256

@dataclass(frozen=True, slots=True)
class Command:
    tenant_id: str
    subject_id: str
    attributes: dict[str, str]

@dataclass(frozen=True, slots=True)
class AuditEvent:
    operation: str
    tenant_id: str
    subject_id: str
    reservation: str
    amount: Decimal
    metadata: dict[str, str]

def ensure_tenant(command: Command) -> None:
    if not command.tenant_id.strip() or not command.subject_id.strip():
        raise ValueError("tenant and subject are required")

def reserve_idempotency(command: Command, *, operation: str, attempt: int) -> str:
    raw = f"{command.tenant_id}:{command.subject_id}:{operation}:{attempt}"
    return sha256(raw.encode()).hexdigest()

def money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
