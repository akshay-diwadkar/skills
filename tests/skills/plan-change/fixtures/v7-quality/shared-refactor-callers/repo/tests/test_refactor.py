from src.lib import normalize
from src.consumer_a import clean

def test_refactor():
    assert normalize(" X ") == "x"
    assert clean(" X ") == "x"
