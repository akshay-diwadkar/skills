# Implementation Hazards Catalog

Use these decisions exactly. The canonical Mechanical Propagation Gate and Non-Destructive Recovery protocol remain authoritative.

## Dirty or Concurrent User Work

- Unrelated dirty path: allow it, snapshot its hash, and require byte-for-byte preservation.
- Dirty plan target before editing: stop unless the user explicitly authorizes incorporation; record that authorization.
- Target changes after its last snapshot: stop immediately. Do not overwrite or attempt automatic whole-file recovery.

## Stale or Contradictory Plan

- Shifted line with the same anchored behavior: record the cosmetic drift and continue.
- Changed behavior, missing anchor, missing dependency, or incompatible version: stop and mark affected `CH/T` records unresolved.
- Do not reinterpret the approved behavior or create a workaround.

## Partial Patch State

- Keep a completed slice only when it is independently correct, has no orphaned symbols, and passes its focused verification.
- Reverse dependent work only through exact agent-hunk evidence whose after-context still matches.
- If hunk ownership or context is uncertain, leave the file untouched and request direction.

## Omitted Caller or Fixture

- Run the Mechanical Propagation Gate.
- A deterministic caller argument or fixture-shape update using a plan-specified value may qualify.
- Changed business behavior, error semantics, or an unspecified expected assertion never qualifies.
- Record every allowed edit as `mechanical-propagation` and report the plan gap.

## Generated Artifact Drift

- Regenerate artifacts named by the plan using the plan command.
- Permit an omitted artifact only when generation is deterministic, expected, bounded, and introduces no dependency/version churn.
- Stop on unexpected transitive updates, snapshots with unexplained changes, migrations, or generated public-contract changes.

## Missing Dependency, Secret, or External System

- Follow an explicit plan installation/configuration step when authorized.
- Otherwise stop. Do not install an omitted dependency, invent a secret, create placeholder credentials, or silently substitute a mock service.
- Record verification as blocked with the exact missing prerequisite.

## Verification Failure

- A plan test failure belongs to its owning `CH-n` unless the test diverges from `T-n`.
- An existing failure is pre-existing only when the same baseline command failed before editing.
- Without a matching baseline result, use `unknown-baseline`; do not fix unrelated code to make the suite green.
- Unexpected resource exhaustion or duration: narrow the check, investigate a change-caused loop/query/recursion risk, and report remaining limits honestly.

## Unsafe or External Operation

- Stop before destructive filesystem/Git actions, migrations, production writes, irreversible effects, or external communication not explicitly authorized by the approved plan and current user request.
- Verification commands do not create authority beyond the approved scope.
- Record the blocked operation and required authorization rather than simulating success.

## Impossible Dependency Order

- Recheck the dependency analysis.
- If the cycle is purely representational and one atomic edit is explicitly covered by the same plan records, combine it and record the relationship.
- Otherwise stop and require plan revision; do not implement downstream records around the cycle.
