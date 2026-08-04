from src.store import fetch

def test_fetch():
    assert fetch("hot") == "cached"
