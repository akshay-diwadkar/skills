"""Database-backed transactional outbox used by integration verification."""
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
