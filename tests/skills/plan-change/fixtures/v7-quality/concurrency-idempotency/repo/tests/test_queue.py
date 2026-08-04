from src.queue import claim_job

def test_claim_once():
    assert claim_job("j-1")
    assert not claim_job("j-1")
