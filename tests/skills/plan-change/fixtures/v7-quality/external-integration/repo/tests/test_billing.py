from src.billing import charge

def test_charge():
    assert charge(5, "k-1") == "charged:5:k-1"
