from src.names import normalize_name

def test_normalize():
    assert normalize_name(" x ") == "x"
