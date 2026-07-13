
# Worked Examples

These examples demonstrate the reasoning process, not just the output format. Study how evidence drives decisions, not how sections are arranged.

## Tiny Example: Adding a Null Guard to normalize_name

### The request
"Fix normalize_name so it handles a missing value without changing valid strings."

### Gate 0 — Orient
- Task type: Bug fix
- Blast radius estimate: Single function, likely 1-3 callers
- Tier: Tiny (one local, reversible behavior, no public API or schema)

### Gate 1 — Frame
- Observable outcome: `normalize_name(None)` returns a safe value instead of raising `AttributeError`
- Success: Null input handled; all existing non-null behavior unchanged

### Gate 2 — Prove Current State (evidence gathering)

**Search sequence:**
```
grep -rn "normalize_name" → names.py:5, test_names.py:8, test_names.py:12
```

**Read names.py:**
```python
# names.py:5
def normalize_name(name: str) -> str:
    return name.strip().lower()  # line 6
```
- Fact: `names.py:6` — calls `.strip()` on `name` before any null check.
- Fact: `names.py:5` — type hint says `str`, not `Optional[str]`.
- Fact: `None.strip()` raises `AttributeError`.

**Read tests:**
```python
# test_names.py:8
def test_normalizes_casing():
    assert normalize_name("Alice") == "alice"

# test_names.py:12  
def test_strips_whitespace():
    assert normalize_name("  Bob  ") == "bob"
```
- Fact: No test for `None` input.
- Fact: No test for empty string input.
- Gap: Empty string behavior is untested but returns `""` (verified by reading line 6).

**Trace callers:**
```
grep -rn "normalize_name" --include="*.py" | grep -v test | grep -v def
→ app.py:23: display = normalize_name(user.name)
→ cli.py:41: key = normalize_name(input_val)
```
- Fact: `app.py:23` — `user.name` could be `None` if the field is optional in the DB.
- Fact: `cli.py:41` — `input_val` comes from user input, theoretically always a string.

**Contradictions:** None found. Comments and code agree.

### Gate 3 — Model the Problem
- Root cause: `name.strip()` at `names.py:6` is called before any null check.
- The fix belongs at the entry of the function, not at each caller.
- Empty string currently returns `""` — this is valid behavior and must be preserved.

### Gate 4 — Decide
- **Option A**: Add `if name is None: return ""` before `.strip()`. Preserves type hint as `str`.
- **Option B**: Change signature to `Optional[str]` and return `None` for `None` input.
- **Selected: A** — because both callers currently expect a `str` return (Fact: `app.py:23` assigns to a display variable, `cli.py:41` uses as a dict key). Returning `None` would break callers.
- **Rejected: B** — would require updating callers to handle `Optional[str]` return, expanding scope.

### Gate 5 — Specify + Trace
```
## Change
names.py:6 — add null guard before .strip():

def normalize_name(name: str) -> str:
    if name is None:
        return ""
    return name.strip().lower()

Preserved: non-None string behavior unchanged (strip + lower).
Preserved: empty string returns "".
Preserved: return type remains str.
```

### Gate 6 — Attack
- **A1 Forgotten Caller**: Both callers (`app.py:23`, `cli.py:41`) receive `str` before and after. No change needed. ✓
- **A2 Empty Input**: `normalize_name("")` → `""` (unchanged, `.strip()` on empty string = `""`). ✓
- **A2 Whitespace-only**: `normalize_name("   ")` → `""` (unchanged). ✓
- No P0/P1 findings.

### Gate 7 — Verify
```
## Verification
- normalize_name(None) → "" (new behavior)
- normalize_name("Alice") → "alice" (unchanged)
- normalize_name("  Bob  ") → "bob" (unchanged)
- normalize_name("") → "" (unchanged)
- `python -m pytest test_names.py` → all pass + new test passes

## Assumptions
- Low-impact: callers that pass None will now silently get "" instead of crashing.
  This is the desired behavior per the request.
```

---

## Standard Example: Adding CSV Export Through Existing Route

### The request
"Add CSV export for completed reports through the existing HTTP route and service."

### Gate 0 — Orient
- Task type: Feature (cross-layer: route → service → response)
- Blast radius estimate: Route file, service file, response helpers, tests
- Tier: Standard (multi-file, multi-layer, internal interface change)

### Gate 2 — Prove Current State (abbreviated to show key reasoning)

**Critical evidence gathered:**
- Fact: `route.py:12` — `GET /reports/:id` calls `service.load_report(id, tenant_id)` then `responses.json_ok(report)`.
- Fact: `route.py:8` — route checks `report.status == 'completed'` and returns 403 if not.
- Fact: `service.py:15` — `load_report` filters by `tenant_id` (tenant isolation exists).
- Fact: `responses.py:3` — `json_ok` sets `Content-Type: application/json`.
- Fact: `responses.py:7` — `csv_ok` already exists in responses.py, sets `Content-Type: text/csv` and `Content-Disposition: attachment`.
- Fact: No test for CSV response path.

**Key insight from analogue search:**
Grepped for other uses of `csv_ok` → Found in `billing_route.py:34` which uses `Accept` header to switch between JSON and CSV. This is the local precedent.

### Gate 4 — Decide (showing reasoning, not just conclusion)

**Question: How does the client request CSV vs JSON?**
- Option A: Query parameter `?format=csv`
- Option B: `Accept` header `text/csv`
- **Selected: B** — because `billing_route.py:34` uses `Accept` header (local precedent). Introducing a query parameter would be a new pattern.

**Question: What fields appear in CSV?**
- Could ask the user, but the report object's fields are visible at `service.py:20`. Using all non-internal fields follows the JSON response's existing behavior.
- **Decision**: Same fields as JSON response, excluding `_internal_id`. No user question needed.

### Gate 5 — Specify + Trace (showing traceability built inline)

```
SC-1: GET /reports/:id with Accept: text/csv returns CSV for completed reports.
SC-2: JSON response behavior is unchanged.
SC-3: Tenant isolation is preserved for CSV path.

CH-1: route.py — add Accept header check after completion validation:
  if request.accepts('text/csv'):
      return responses.csv_ok(report.to_csv_row(), filename=f"report-{id}.csv")
  return responses.json_ok(report)

CH-2: service.py — add to_csv_row() method to Report:
  def to_csv_row(self) -> list[str]:
      return [self.id, self.title, self.created_at, self.status]
  (Excludes _internal_id per decision above.)

Traceability:
| SC | CH | T | Status |
|---|---|---|---|
| SC-1 | CH-1, CH-2 | T-1 | New |
| SC-2 | CH-1 | T-2 | Preserved |
| SC-3 | CH-1 | T-3 | Preserved |

Propagation:
- route.py:12 → CH-1 → update required: yes — add Accept check
- service.py:15 → CH-2 → update required: yes — add to_csv_row
- responses.py:7 → no change — csv_ok already exists
- test_route.py → update required: yes — add T-1, T-2, T-3
```

### Gate 6 — Attack (showing real vs. cosmetic findings)

**Real finding (P1):**
> R-1 P1 [A2 Empty Input]: If `report.to_csv_row()` returns fields containing commas or quotes, the CSV output will be malformed. `responses.csv_ok` at `responses.py:7` does not escape fields.
> Consequence: Downloaded CSV cannot be parsed by Excel.
> Resolution: CH-2 must use Python's `csv` module with proper quoting, or CH-1 must pass through `csv.writer`. Update CH-2 to use `csv.writer` with `QUOTE_MINIMAL`.

**Dismissed attack (with evidence):**
> A1 Forgotten Caller: No other code calls `to_csv_row` — it's a new method. No callers to miss. ✓
> A3 Concurrent Request: CSV export is read-only. No shared state mutation. ✓

---

## Common Mistakes: Bad vs. Good

### Vague evidence vs. specific evidence

❌ **Bad:**
> Current State: The route handles report loading and validation.

✅ **Good:**
> Current State:
> - Fact: `route.py:8` — validates `report.status == 'completed'`, returns 403 if not
> - Fact: `route.py:12` — calls `service.load_report(id, tenant_id)`, tenant-scoped
> - Fact: `responses.py:7` — `csv_ok` helper already exists with proper Content-Type

### Cosmetic vs. real adversarial finding

❌ **Bad:**
> R-1 P2: Consider adding logging for CSV downloads.
> R-2 P2: The CSV filename could be more descriptive.
> R-3 P2: Consider rate-limiting CSV downloads.

✅ **Good:**
> R-1 P1 [A2 Empty Input]: Report titles containing commas will produce malformed CSV rows because `responses.csv_ok` does not escape fields. Resolution: Use `csv.writer` with `QUOTE_MINIMAL` in CH-2.

### Deferred vs. resolved decision

❌ **Bad:**
> The CSV format will be determined during implementation based on the report structure.

✅ **Good:**
> CSV columns: id, title, created_at, status (same fields as JSON response, excluding _internal_id per `service.py:20`). Header row included. Fields quoted with `csv.QUOTE_MINIMAL`.

### Missing vs. complete propagation

❌ **Bad:**
> Update route.py and service.py. Update tests as needed.

✅ **Good:**
> Propagation:
> - `route.py:12` → CH-1 → update required: yes — add Accept header check
> - `service.py:15` → CH-2 → update required: yes — add to_csv_row method
> - `responses.py:7` → no change — csv_ok already exists, verified at responses.py:7
> - `test_route.py:1` → update required: yes — add T-1 (CSV happy path), T-2 (JSON unchanged), T-3 (tenant isolation for CSV)
> - `openapi.yaml:45` → update required: no — CSV is content-negotiated, same endpoint
