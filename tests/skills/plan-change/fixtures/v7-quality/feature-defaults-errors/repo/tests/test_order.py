from src.order import place_order

def test_default_shipping():
    assert place_order(["a"], None) == "a|standard"

def test_invalid_shipping():
    try:
        place_order(["a"], "overnight")
        raise AssertionError("expected rejection")
    except ValueError:
        pass
