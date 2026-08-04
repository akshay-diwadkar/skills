from src.scan import scan

def test_scan():
    assert scan(["a", "longer"]) == ["longer"]
