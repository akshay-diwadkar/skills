# Devil's Advocate Protocol

Run this after drafting every plan. Assume the plan will fail and find at least three concrete failure modes before finalizing.

## Attack Vectors

1. Literal interpretation attack: what breaks if the implementer follows the plan exactly in a context the draft did not consider?
2. Missing edge case attack: what input, state, permission, empty value, legacy value, or timing condition breaks the logic?
3. Dependency surprise attack: what if a library, API, shared helper, generated client, or service behaves differently than assumed?
4. Concurrency or ordering attack: what if operations happen in another order, retry, interleave, or run twice?
5. Partial failure attack: what if step N succeeds but step N+1 fails? Is the system still valid?
6. Scale attack: what happens at 10x, 100x, or 1000x expected volume?

## Required Output

For each finding, include:

- Failure scenario: the exact state, input, dependency behavior, or execution order.
- Why the draft fails: the missing plan detail or wrong assumption.
- Resolution: modify the plan, or explicitly accept the risk with evidence.
- Severity: P0, P1, or P2.

Finding shape:

```text
- P1 literal interpretation: If [scenario], the draft tells the implementer to [ambiguous/bad step]. Fix: change [section] to specify [exact behavior].
```

## Rules

- If any finding is P0, modify the plan before finalization. No exceptions.
- If the same root cause appears in multiple findings, fix the root cause once and cite the affected findings.
- Do not list generic risks. Every finding must point to a concrete plan instruction, code path, dependency, input, or assumption.
- If fewer than three real findings exist, state the explored attack vectors and the repo evidence proving they are not material.
