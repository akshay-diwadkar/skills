from src.feature import feature_name


def test_old_feature_name() -> None:
    assert feature_name() == "old"
