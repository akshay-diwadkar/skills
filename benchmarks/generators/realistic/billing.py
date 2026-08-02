"""Atlas Billing Platform fixture emitter (Python service plus TypeScript SDK)."""

from __future__ import annotations

from pathlib import Path

from .common import asset_text, generated_provenance, json_text, require_empty_output, write


def _write_reference_flows(output: Path) -> None:
    """Write the small set of intentionally named, cross-layer benchmark flows."""
    write(output, "services/domain/invoice_pricing.py", '''"""Canonical invoice pricing with currency precision and tenant isolation."""
from decimal import Decimal
from services.shared.runtime import AuditEvent, Command, ensure_tenant, money, reserve_idempotency

def price_invoice(command: Command) -> AuditEvent:
    ensure_tenant(command)
    subtotal = money(Decimal(command.attributes["subtotal"]))
    tax_rate = Decimal(command.attributes.get("tax_rate", "0"))
    total = money(subtotal + subtotal * tax_rate)
    return AuditEvent("invoice.price", command.tenant_id, command.subject_id,
                      reserve_idempotency(command, operation="invoice.price", attempt=0),
                      total, {"policy": "currency-minor-unit", "ledger": "invoice"})
''')
    write(output, "services/persistence/idempotency_store.py", '''"""Tenant-qualified idempotency reservation used before billing mutations."""
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
''')
    write(output, "services/workers/outbox_publisher.py", '''"""Transactional outbox publisher with bounded retries and poison isolation."""
from dataclasses import dataclass

@dataclass(frozen=True)
class PendingEvent:
    event_id: str
    tenant_id: str
    attempts: int

def publish_batch(events: list[PendingEvent], publish) -> tuple[list[str], list[str]]:
    published, quarantined = [], []
    for event in events:
        if event.attempts >= 4:
            quarantined.append(event.event_id)
            continue
        publish(event.tenant_id, event.event_id)
        published.append(event.event_id)
    return published, quarantined
''')
    write(output, "services/persistence/sqlite_outbox.py", '''"""Database-backed transactional outbox used by integration verification."""
import json
import sqlite3
from dataclasses import dataclass

@dataclass(frozen=True)
class OutboxRecord:
    event_id: str
    tenant_id: str
    payload: dict[str, object]

class SqliteOutbox:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def append(self, record: OutboxRecord) -> None:
        with self.connection:
            self.connection.execute("INSERT INTO event_outbox(id, tenant_id, payload) VALUES (?, ?, ?)",
                                    (record.event_id, record.tenant_id, json.dumps(record.payload, sort_keys=True)))

    def pending_for_tenant(self, tenant_id: str) -> list[OutboxRecord]:
        rows = self.connection.execute("SELECT id, tenant_id, payload FROM event_outbox WHERE tenant_id = ? AND published_at IS NULL ORDER BY id", (tenant_id,))
        return [OutboxRecord(event_id, tenant, json.loads(payload)) for event_id, tenant, payload in rows]
''')
    write(output, "services/entitlements/grant_service.py", '''"""Grant entitlements only after the paid invoice event is committed."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Grant:
    tenant_id: str
    account_id: str
    feature: str
    source_invoice: str

def grant_paid_feature(tenant_id: str, account_id: str, feature: str, invoice_state: str, invoice_id: str) -> Grant:
    if invoice_state != "paid":
        raise ValueError("entitlements require a paid invoice")
    return Grant(tenant_id, account_id, feature, invoice_id)
''')
    write(output, "services/domain/refund_policy.py", '''"""Refund eligibility policy preserving settled-ledger invariants."""
from decimal import Decimal

def refundable_amount(charged: Decimal, already_refunded: Decimal, requested: Decimal) -> Decimal:
    if charged < 0 or already_refunded < 0:
        raise ValueError("settled ledger amounts must be non-negative")
    remaining = charged - already_refunded
    if requested <= 0 or requested > remaining:
        raise ValueError("refund exceeds the remaining settled amount")
    if remaining == 0:
        raise ValueError("a fully refunded charge has no refundable balance")
    return requested
''')
    write(output, "services/subscriptions/renewal_policy.py", '''"""Subscription renewal eligibility at the billing clock boundary."""
from datetime import datetime, timezone

def renewal_is_due(period_end: datetime, now: datetime, status: str) -> bool:
    if period_end.tzinfo is None or now.tzinfo is None:
        raise ValueError("renewal timestamps must be timezone-aware")
    if status not in {"active", "past_due"}:
        return False
    return period_end.astimezone(timezone.utc) <= now.astimezone(timezone.utc)
''')
    write(output, "sdk/merchant/entitlement_client.ts", '''import { AtlasClient, RequestContext, validateContext } from "../shared/runtime.js";

/** Maintained merchant boundary for reading paid-invoice entitlements. */
export async function fetchPaidEntitlements(client: AtlasClient, context: RequestContext) {
  validateContext(context);
  const idempotencyKey = `${context.tenantId}:${context.subjectId}:entitlements`;
  const request = {
    path: "/v1/entitlements/paid" as const,
    method: "POST" as const,
    idempotencyKey,
    body: context,
  };
  return client.request(request);
}
''')
    write(output, "services/api/billing_facade.py", '''"""Application boundary coordinating invoice settlement and entitlement delivery."""
from dataclasses import dataclass
from services.domain.invoice_pricing import price_invoice
from services.entitlements.grant_service import Grant, grant_paid_feature
from services.persistence.idempotency_store import IdempotencyStore
from services.shared.runtime import AuditEvent, Command
from services.workers.outbox_publisher import PendingEvent, publish_batch

@dataclass(frozen=True)
class SettlementResult:
    invoice: AuditEvent
    grant: Grant
    published_event_ids: tuple[str, ...]

def settle_invoice(command: Command, store: IdempotencyStore, publish) -> SettlementResult:
    """Price and settle one invoice while preserving the tenant idempotency boundary."""
    invoice = price_invoice(command)
    if not store.reserve(command.tenant_id, invoice.reservation, str(invoice.amount)):
        raise RuntimeError("invoice reservation could not be acquired")
    grant = grant_paid_feature(command.tenant_id, command.subject_id,
                               command.attributes["feature"], "paid", command.subject_id)
    published, quarantined = publish_batch(
        [PendingEvent(f"invoice-paid:{command.subject_id}", command.tenant_id, 0)], publish)
    if quarantined:
        raise RuntimeError("new invoice event was unexpectedly quarantined")
    return SettlementResult(invoice, grant, tuple(published))
''')
    write(output, "config/billing/currency-policy.yaml", "policy: currency-minor-unit\nrounding: half-up\nscale: 2\n")
    write(output, "config/persistence/idempotency-policy.yaml", "scope: tenant-and-key\nreject_payload_mismatch: true\nretention_hours: 72\n")
    write(output, "config/workers/outbox-policy.yaml", "max_attempts: 4\nquarantine: poison-events\nordering: tenant\n")
    write(output, "config/entitlements/grant-policy.yaml", "required_invoice_state: paid\nrevoke_on_refund: true\n")
    write(output, "config/subscriptions/renewal-policy.yaml", "eligible_statuses: [active, past_due]\nclock: utc\n")
    write(output, "tests/domain/test_invoice_pricing.py", '''from decimal import Decimal
from services.domain.invoice_pricing import price_invoice
from services.shared.runtime import Command

def test_invoice_pricing_applies_minor_unit_rounding() -> None:
    event = price_invoice(Command("tenant-a", "invoice-a", {"subtotal": "10.005", "tax_rate": "0.20"}))
    assert event.amount == Decimal("12.01")
    assert event.metadata["policy"] == "currency-minor-unit"
''')
    write(output, "tests/persistence/test_idempotency_store.py", '''import pytest
from services.persistence.idempotency_store import IdempotencyStore

def test_payload_mismatch_is_rejected_within_a_tenant() -> None:
    store = IdempotencyStore()
    assert store.reserve("tenant-a", "renewal-1", "digest-a")
    with pytest.raises(ValueError, match="different payload"):
        store.reserve("tenant-a", "renewal-1", "digest-b")
''')
    write(output, "tests/workers/test_outbox_publisher.py", '''from services.workers.outbox_publisher import PendingEvent, publish_batch

def test_poison_events_are_quarantined_without_blocking_the_batch() -> None:
    calls = []
    published, quarantined = publish_batch([PendingEvent("ok", "tenant-a", 0), PendingEvent("poison", "tenant-a", 4)], lambda *x: calls.append(x))
    assert published == ["ok"]
    assert quarantined == ["poison"]
    assert calls == [("tenant-a", "ok")]
''')
    write(output, "tests/integration/test_sqlite_outbox.py", '''import sqlite3
from pathlib import Path
from services.persistence.sqlite_outbox import OutboxRecord, SqliteOutbox

def test_migration_and_repository_preserve_tenant_isolation() -> None:
    connection = sqlite3.connect(":memory:")
    migration = (Path(__file__).parents[2] / "migrations/20250101_create_event_outbox.sql").read_text(encoding="utf-8")
    connection.executescript(migration)
    outbox = SqliteOutbox(connection)
    outbox.append(OutboxRecord("event-a", "tenant-a", {"kind": "invoice.paid"}))
    outbox.append(OutboxRecord("event-b", "tenant-b", {"kind": "invoice.paid"}))
    assert [record.event_id for record in outbox.pending_for_tenant("tenant-a")] == ["event-a"]
''')
    write(output, "tests/entitlements/test_grant_service.py", '''import pytest
from services.entitlements.grant_service import grant_paid_feature

def test_entitlement_requires_a_paid_invoice() -> None:
    with pytest.raises(ValueError, match="paid invoice") as error:
        grant_paid_feature("tenant-a", "account-a", "analytics", "open", "invoice-a")
    assert "paid invoice" in str(error.value)
''')
    write(output, "tests/domain/test_refund_policy.py", '''from decimal import Decimal
from services.domain.refund_policy import refundable_amount

def test_refund_is_limited_by_the_settled_remainder() -> None:
    # Refund balances are evaluated inside one tenant ledger.
    assert refundable_amount(Decimal("20"), Decimal("3"), Decimal("7")) == Decimal("7")
''')
    write(output, "tests/subscriptions/test_renewal_policy.py", '''from datetime import datetime, timezone
from services.subscriptions.renewal_policy import renewal_is_due

def test_active_subscription_renews_when_its_utc_period_has_ended() -> None:
    period_end = datetime(2025, 1, 1, tzinfo=timezone.utc)
    now = datetime(2025, 1, 2, tzinfo=timezone.utc)
    assert renewal_is_due(period_end, now, "active")
    assert not renewal_is_due(period_end, now, "cancelled")
''')
    write(output, "tests/merchant/entitlement-client.test.ts", '''import test from "node:test";
import assert from "node:assert/strict";
import { fetchPaidEntitlements } from "../../sdk/merchant/entitlement_client.js";
import { AtlasClient } from "../../sdk/shared/runtime.js";

test("merchant entitlement reads carry a tenant-qualified idempotency key", async () => {
  const requests: Array<{ idempotencyKey: string }> = [];
  const client = new AtlasClient(async request => { requests.push(request); return { ok: true }; });
  await fetchPaidEntitlements(client, { tenantId: "tenant-a", subjectId: "account-a", attributes: {} });
  assert.equal(requests[0].idempotencyKey, "tenant-a:account-a:entitlements");
});
''')
    write(output, "tests/api/test_billing_facade.py", '''from services.api.billing_facade import settle_invoice
from services.persistence.idempotency_store import IdempotencyStore
from services.shared.runtime import Command

def test_settlement_prices_grants_and_publishes_as_one_application_flow() -> None:
    deliveries: list[tuple[str, str]] = []
    result = settle_invoice(
        Command("tenant-a", "invoice-a", {"subtotal": "10", "feature": "analytics"}),
        IdempotencyStore(),
        lambda tenant, event: deliveries.append((tenant, event)),
    )
    assert result.invoice.amount == 10
    assert result.grant.feature == "analytics"
    assert deliveries == [("tenant-a", "invoice-paid:invoice-a")]
''')
    write(output, "sdk-test/entitlement-client.test.mjs", '''import test from "node:test";
import assert from "node:assert/strict";
import { AtlasClient } from "../dist/sdk/shared/runtime.js";
import { fetchPaidEntitlements } from "../dist/sdk/merchant/entitlement_client.js";

test("merchant entitlement requests carry a tenant-qualified idempotency key", async () => {
  const requests = [];
  const client = new AtlasClient(async request => { requests.push(request); return { ok: true }; });
  await fetchPaidEntitlements(client, { tenantId: "tenant-a", subjectId: "account-a", attributes: {} });
  assert.equal(requests[0].idempotencyKey, "tenant-a:account-a:entitlements");
});
''')


def emit(output: Path) -> None:
    require_empty_output(output)
    write(output, ".gitignore", ".venv/\nnode_modules/\ndist/\n.pytest_cache/\n")
    write(output, "README.md", "# Atlas Billing Platform\n\nTenant-isolated billing, outbox, and merchant SDK fixture.\n")
    write(output, "docs/operations.md", "# Operations\n\nWorkers publish the tenant-scoped event outbox after bounded retries.\n")
    write(output, "pyproject.toml", "[project]\nname = 'atlas-billing'\nversion = '0.1.0'\nrequires-python = '>=3.11'\ndependencies = ['fastapi==0.115.6', 'sqlalchemy==2.0.36']\n\n[tool.pytest.ini_options]\ntestpaths = ['tests']\npythonpath = ['.']\n")
    write(output, "requirements.lock", asset_text("billing-requirements.lock"))
    write(output, "package.json", json_text({"name": "@atlas/admin-sdk", "private": True, "type": "module", "scripts": {"build": "tsc -p tsconfig.json", "test": "node --test sdk-test/*.test.mjs"}, "devDependencies": {"typescript": "5.7.2"}}))
    write(output, "package-lock.json", asset_text("billing-package-lock.json"))
    write(output, "tsconfig.json", json_text({"compilerOptions": {"target": "ES2022", "module": "NodeNext", "moduleResolution": "NodeNext", "strict": True, "outDir": "dist"}, "include": ["sdk/**/*.ts", "generated/**/*.ts"]}))
    write(output, "services/__init__.py", "")
    write(output, "services/api/__init__.py", "")
    write(output, "services/subscriptions/__init__.py", "")
    write(output, "services/shared/__init__.py", "")
    write(output, "services/shared/runtime.py", '''from dataclasses import dataclass\nfrom decimal import Decimal, ROUND_HALF_UP\nfrom hashlib import sha256\n\n@dataclass(frozen=True, slots=True)\nclass Command:\n    tenant_id: str\n    subject_id: str\n    attributes: dict[str, str]\n\n@dataclass(frozen=True, slots=True)\nclass AuditEvent:\n    operation: str\n    tenant_id: str\n    subject_id: str\n    reservation: str\n    amount: Decimal\n    metadata: dict[str, str]\n\ndef ensure_tenant(command: Command) -> None:\n    if not command.tenant_id.strip() or not command.subject_id.strip():\n        raise ValueError("tenant and subject are required")\n\ndef reserve_idempotency(command: Command, *, operation: str, attempt: int) -> str:\n    raw = f"{command.tenant_id}:{command.subject_id}:{operation}:{attempt}"\n    return sha256(raw.encode()).hexdigest()\n\ndef money(value: Decimal) -> Decimal:\n    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)\n''')
    write(output, "sdk/shared/runtime.ts", '''export type RequestContext = Readonly<{
  tenantId: string;
  subjectId: string;
  attributes: Record<string, string>;
}>;
export type Request = Readonly<{ path: string; method: "POST"; idempotencyKey: string; body: object }>;
export class AtlasClient {
  constructor(private readonly transport: (request: Request) => Promise<unknown>) {}
  request(request: Request) { return this.transport(request); }
}
export function validateContext(context: RequestContext): void {
  if (!context.tenantId || !context.subjectId) throw new Error("tenant and subject are required");
}
''')
    write(output, "schemas/change-event.json", json_text({"type": "object", "required": ["tenant_id", "event_type", "revision"], "properties": {"tenant_id": {"type": "string"}, "event_type": {"type": "string"}, "revision": {"type": "integer"}}}))
    write(output, "generated/contracts.ts", generated_provenance(source="schemas/change-event.json", input_value="change-event-v1") + "export interface ChangeEvent { tenant_id: string; event_type: string; revision: number }\n")
    write(output, "migrations/20250101_create_event_outbox.sql", "CREATE TABLE event_outbox (id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, payload JSON NOT NULL, published_at TIMESTAMP NULL);\n")
    _write_reference_flows(output)
