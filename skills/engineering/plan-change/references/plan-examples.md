# Plan examples

Read only when calibrating tiny or standard depth. These show reasoning and
implementation guidance, not ceremony.

## Tiny bug-fix

**Request intent:** `normalize_name(None)` returns `''` without changing strip
behavior for present strings.

**Why tiny:** One owning function, one preserved behavior, no shared fan-out.

**Explore:** Open `src/names.py`, confirm `normalize_name` owns the null path,
and note present-string strip already works.

**Plan shape:** One RQ from the request, one SC that preserves strip behavior,
one F on the owner, one local CH, one T that fails before the fix and passes
after. Skip Decisions/Propagation unless the change becomes shared.

**Implementation guidance:** Return early for absent values; leave the strip
path untouched; cite the exact owner lines; do not invent caller CH records.

## Standard shared refactor

**Request intent:** Clarify the `normalize_name` owner while updating the package
re-export and one caller.

**Why standard:** Shared locality, real caller/re-export surfaces, dependency
between owner and consumers.

**Explore:** Trace `normalize_name`, `src/__init__.py` re-export, and
`src/caller.py`. One bounded sweep decides which surfaces change.

**Plan shape:** Obligations for the refactor and preserved strip behavior;
owner + caller/re-export CH with `depends_on`; one P that can list related
shared owners when the same sweep conclusion applies; verification covering
every SC/CH.

**Implementation guidance:** Change the owner first, then dependents; keep
strip behavior identical; record distinct propagation paths; do not add risk or
rollout sections unless a risk domain applies.
