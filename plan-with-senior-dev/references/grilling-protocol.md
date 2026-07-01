# Grilling Protocol (Checklist)

Quick-reference for pressure-testing decisions during §2 Grill to Shared Understanding.

**Pressure Tests** — for each major decision, test one concrete scenario:
- Happy path: realistic data, expected flow.
- Boundary: empty, missing, duplicate, stale, oversized, or invalid data.
- Failure: dependency unavailable, permission denied, validation failed, race, or rollback.
- Compatibility: old clients, existing data, old configs, or previous behavior.

**Assumption Handling**:
- Name it. Classify it (product/technical/domain/migration/test).
- If non-blocking, record default and why safe.
- If blocking, ask the narrowest question that resolves it.

**Domain Alignment** — when business language appears:
- Check `CONTEXT.md`/`CONTEXT-MAP.md` before accepting new terms.
- Call out conflicts between user, code, and docs. Propose one canonical term.

**Exit Criteria** — stop grilling only when all are true:
- Goal concrete, terms agreed, concepts bounded.
- Referenced artifacts checked (or marked as assumptions).
- Scope, interfaces, data shapes, edge cases decided.
- Migration/compatibility/rollback/docs settled where relevant.
- Test strategy proves the risky behavior.
- No "decide later" or unresolved P0 risks remain.
