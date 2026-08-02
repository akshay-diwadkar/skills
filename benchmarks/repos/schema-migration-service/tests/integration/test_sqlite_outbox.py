import sqlite3
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
