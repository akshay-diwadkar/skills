from src.target import target

def test_present():
    assert target(" x ") == "x"

def test_absent():
    assert target(None) == ""
