# Resolver Before/After

The historical owner precision mixed all three phases and is not directly comparable to primary-owner precision.

| Metric | Before | After | Held-out |
| --- | ---: | ---: | ---: |
| Hit@1 | 0.806 | 0.944 | 1.000 |
| Hit@3 | 0.972 | 1.000 | 1.000 |
| MRR | 0.884 | 0.972 | 1.000 |
| Primary-owner precision | legacy 0.364 | 0.944 | 1.000 |
| Primary-owner recall | legacy 0.780 | 0.944 | 1.000 |

Runtime IDF is derived only from the repository being resolved. Resolver modules do not import fixtures; tuning and held-out cases are hash-bound and reported separately.
