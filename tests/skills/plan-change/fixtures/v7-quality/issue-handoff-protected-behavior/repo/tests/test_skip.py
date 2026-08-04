from src.skip import run

def test_run():
    assert run("plain") == "skipped"
    assert run("verbose") == "running"
