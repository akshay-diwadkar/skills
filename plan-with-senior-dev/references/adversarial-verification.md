# Adversarial Verification

Attack the completed draft, repair findings in their owning changes/tests, and record each required attack as repaired, dismissed, or not applicable with evidence. Never invent findings to satisfy a count.

## Attacks

- **A1 Forgotten caller:** search direct and transitive consumers, re-exports, fixtures, configuration, generated clients, deployment surfaces, and docs.
- **A2 Boundary input:** exercise applicable null, empty, zero, negative, maximum, invalid-type, unmatched, and default cases.
- **A3 Concurrent request:** test simultaneous state changes, retry after timeout, duplicate delivery, cancellation, and the worst material interleaving.
- **A4 Rollback:** assume new code processed real durable or external work before rollback; verify old readers/writers, queued work, caches, and irreversible effects.
- **A5 Scale surprise:** test 10× and 100× plausible volume for N+1 I/O, unbounded memory, pagination, transaction length, and contention.
- **A6 Literal implementation:** read each change and blueprint as a literal implementer; verify types, branches, errors, ordering, side effects, and caller ownership are sufficient.

## Blueprint Fidelity

Compare every pseudocode branch, Mermaid edge/state, interface shape, and table row with its owning `CH-n`, constraints, risks, and `T-n` expectations. Repair contradictions in both representations; do not accept “the prose is authoritative” as a dismissal.

## Severity and Completion

- P0: data loss, security breach, silent corruption, or unrecoverable state. Finalization is blocked.
- P1: incorrect behavior, broken consumer, missing failure handling, or unsafe rollback. Repair the owning change and test.
- P2: non-blocking concern. Retain only with explicit acceptance evidence.

Re-open every citation, existing anchor, signature, unchanged claim, trace row, and expected result after repairs. Complete the attack only when no P0/P1 remains and the finalizer accepts the exact draft.
