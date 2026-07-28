# Plan-Change Request
<!-- artifact: request.md; handoff-contract: 1 -->

## Workflow and Success
- Workflow: repeated user loads
- Goal: Remove duplicated work across repeated user loads.
- Success criteria: Preserve output and reduce the five-run warm median below 20 ms.

## Protected Behavior and Constraints
- Protected behavior: Preserve output, errors, ordering, and side effects.
- Constraints: No public behavior change.
- Exclusions: New dependencies and shared mutable caching.

## Winning Candidate
- Candidate: C-1
- Band: strategic-win
- Mechanism: consolidate repeated workflow work at load_users
- Evidence: F-1, B-1, R-1

## Grounded Anchors
- Anchor: `src/system.py:load_users`

## Plan-Change Invocation
- Tier: standard
- Intent: refactor
- Risk domains: none
