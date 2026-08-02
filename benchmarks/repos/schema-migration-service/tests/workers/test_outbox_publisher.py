from services.workers.outbox_publisher import PendingEvent, publish_batch

def test_poison_events_are_quarantined_without_blocking_the_batch() -> None:
    calls = []
    published, quarantined = publish_batch([PendingEvent("ok", "tenant-a", 0), PendingEvent("poison", "tenant-a", 4)], lambda *x: calls.append(x))
    assert published == ["ok"]
    assert quarantined == ["poison"]
    assert calls == [("tenant-a", "ok")]
