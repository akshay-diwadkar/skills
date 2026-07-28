# Apply the Authorized Local Normalization
<!-- optimization-contract: 2; path: fast; scope: targeted; stage: implementation -->

## Fast Path Decision
- Authorization: explicit implementation — user requested the local normalization edit
- F-1: `src/system.py:1` | anchor: `normalize_items` | observation: normalize_items is the only owner of this local transformation.
- B-1: workflow: item normalization | method: static | command: inspect the one bounded list transformation | result: one existing function with one normalization pass | confidence: high | evidence: F-1
- C-1: band: quick-win | eligibility: authorized=yes, targeted=yes, one-file=yes, one-symbol=yes, one-mechanism=yes, behavior-clear=yes, compatibility-clear=yes, acceptance-clear=yes, rollback-clear=yes, low-risk=yes, low-blast-radius=yes, high-confidence=yes, reversible=yes, no-protected-domain=yes, no-overlapping-dirty-change=yes | evidence: F-1, B-1 | anchors: src/system.py:normalize_items | change: apply the validated call-local normalization optimization | benefit: retain one bounded normalization pass | verify: python -m pytest | expected: identical normalized values and errors | rollback: restore normalize_items's previous body
