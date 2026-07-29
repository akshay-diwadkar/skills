from src.evaluation.segment_matcher import matches_segment

assert matches_segment({"country": "IN", "plan": "pro"}, {"country": "IN", "plan": "pro"})
assert not matches_segment({"country": "IN", "plan": "free"}, {"country": "IN", "plan": "pro"})
