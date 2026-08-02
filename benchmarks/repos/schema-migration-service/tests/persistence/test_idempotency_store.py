import pytest
from services.persistence.idempotency_store import IdempotencyStore

def test_payload_mismatch_is_rejected_within_a_tenant() -> None:
    store = IdempotencyStore()
    assert store.reserve("tenant-a", "renewal-1", "digest-a")
    with pytest.raises(ValueError, match="different payload"):
        store.reserve("tenant-a", "renewal-1", "digest-b")
