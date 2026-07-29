from src.evaluation.prerequisite_policy import permits_prerequisite

assert permits_prerequisite(5, 5)
assert not permits_prerequisite(4, 5)
assert not permits_prerequisite(6, 5, enabled=False)
