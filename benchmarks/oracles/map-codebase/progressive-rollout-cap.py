from src.rollouts.progressive_rollout import rollout_percentage

assert rollout_percentage(85, 20, 100) == 100
assert rollout_percentage(20, 5, 100) == 25
