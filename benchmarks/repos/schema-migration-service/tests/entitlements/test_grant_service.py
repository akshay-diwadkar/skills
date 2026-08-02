import pytest
from services.entitlements.grant_service import grant_paid_feature

def test_entitlement_requires_a_paid_invoice() -> None:
    with pytest.raises(ValueError, match="paid invoice") as error:
        grant_paid_feature("tenant-a", "account-a", "analytics", "open", "invoice-a")
    assert "paid invoice" in str(error.value)
