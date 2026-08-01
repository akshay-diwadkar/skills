# Agent-first plan-contract v6

This major release replaces plan-change's stateful v5 discovery pipeline with
native agent exploration and one-pass sealing of an agent-authored v6 draft.
The new runtime verifies only cited files, computes proof hashes automatically,
binds targeted repository evidence, and remains insensitive to unrelated
repository size and changes.

Implement-plan and scope-issue accept v6 while retaining isolated deprecated v5
readers for one release. Design and optimization handoffs no longer depend on
the removed preparation, inventory, or excerpt-hashing commands.
