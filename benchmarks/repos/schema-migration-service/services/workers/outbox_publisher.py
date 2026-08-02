"""Transactional outbox publisher with bounded retries and poison isolation."""
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
