# Cognitive Protocols

Step-by-step reasoning procedures for each planning concern. Follow these protocols literally during gate work. Each protocol specifies concrete actions, expected outputs, and stop conditions.

## Evidence Gathering Protocol

### When to use
Gate 2 (Prove Current State) for every plan.

### Steps

1. **Locate the entry point.** Grep for the function, class, route, handler, or command named in the request. Record every match with `file:line`.
2. **Read the primary file.** Open the file containing the entry point. Record:
   - Full signature (name, parameters with types, return type, decorators/annotations)
   - Every branch (`if/else/switch/match/try-catch`) and what triggers each
   - Every external call (function calls, DB queries, HTTP requests, queue publishes)
   - Every error path (thrown exceptions, returned errors, logged warnings)
3. **Trace one real call path.** Starting from the most common caller of the entry point:
   - Caller → entry point → first dependency → side effect → output
   - For each hop record: `file:line`, argument passed, value received
   - Stop at the first I/O boundary (DB, network, filesystem, queue)
4. **Search for analogues.** Grep for operations in the same module/package that handle a similar concern (e.g., another CRUD endpoint, another validation, another event handler).
   - Record: how the analogue handles error, validation, auth, logging, and response format
   - Record: file:line for each analogous pattern
5. **Find tests.** Grep for the entry point name in test directories.
   - Record: which behaviors are tested, which are not
   - Record: fixture/mock setup that reveals assumptions
   - Record: test file:line for each relevant test
6. **Check configuration and schemas.** Search for config keys, environment variables, schema definitions, migration files, and generated artifacts referenced by the call path.
   - Record: each config/schema surface with file:line
7. **Find contradictions.** Compare:
   - Code behavior vs. comments/docstrings
   - Code behavior vs. README/docs
   - Code behavior vs. test expectations
   - Record each contradiction with file:line for both sides

### Stop when
- Current behavior is cited with file:line (not described from memory)
- Change boundary is explicit (which files/functions/lines will change)
- Invariants are named (what must NOT change)
- Side effects are listed (DB writes, network calls, file mutations, cache updates)
- Blast radius is mapped (callers, consumers, tests, config, schemas)
- Test gaps are identified (what is NOT tested that should be)
- Contradictions are documented or explicitly absent

### Common failures
- **Citing from memory**: Describing what you think the code does instead of reading it. Fix: Always open the file and cite the line number.
- **Single-file tunnel vision**: Reading only the entry point file. Fix: Always trace at least one caller and one dependency.
- **Ignoring tests**: Skipping test files. Fix: Tests reveal assumptions, edge cases, and fixture shapes that the implementation hides.
- **Treating comments as truth**: Comments lie; code doesn't. Fix: When comments and code disagree, record the contradiction and trust the code.

---

## Root Cause Analysis Protocol

### When to use
Bug fix tasks, unexpected behavior, and any request that begins with a symptom.

### Steps

1. **Prove the symptom.** Find the exact line where the incorrect behavior occurs. This is not the line the user reported — it is the line where the code produces the wrong output. Record: `file:line`, the incorrect output, and the expected output.
2. **Why-1: What does this line actually do?** Read the code at the symptom location. What value does it compute? What does it depend on? Cite the dependency with `file:line`.
3. **Why-2: Why does the dependency provide that value?** Trace into the dependency. What logic produces the value that causes the symptom? Cite with `file:line`.
4. **Why-3 and beyond.** Continue only while each "why" is backed by a `file:line` citation. The moment you cannot cite evidence, STOP. You have reached speculation.
5. **Identify the root cause.** The root cause is the deepest "why" with evidence. It is the line of code that, if corrected, would fix the symptom AND prevent the same class of bug from recurring.
6. **Reject symptom-only patches.** If the proposed fix is at the symptom location (Why-1) rather than the root cause, explain why the root cause fix is better. Accept a symptom patch only when explicitly requested for containment.

### Stop when
- The root cause is identified with `file:line`
- The reason it is the root (not just a symptom) is stated
- The fix addresses the root, not the symptom

### Common failures
- **Stopping at Why-1**: Patching where the symptom appears instead of where the defect originates.
- **Speculative whys**: Continuing the chain beyond available evidence. If you can't cite it, don't claim it.
- **Ignoring analogues**: The same root cause often affects similar functions. Always search for analogues.

---

## Interface Change Protocol

### When to use
Any plan that adds, modifies, or removes a public or shared function, API endpoint, event schema, command, or type.

### Steps

1. **Record the current shape.** Read the actual code and write the complete current interface:
   - Name, parameters (with types and defaults), return type, error types
   - Serialization format (JSON keys, query params, headers)
   - Nullability of every field
   - Validation rules
2. **Write the proposed shape.** Show the complete proposed interface in a code block. Do not describe the delta in prose — show the full before and after.
3. **Enumerate consumers.** Search for every file that calls, imports, or references the interface.
   - For each consumer: file:line, how it calls the interface, what it does with the result
4. **Build the compatibility matrix.**
   - Old caller + old interface: works (baseline)
   - Old caller + new interface: what breaks? what works?
   - New caller + old interface: what breaks? (rollback scenario)
   - New caller + new interface: works (target)
5. **Specify the migration path.** If old callers break, specify exactly how each one gets updated. If this is a rolling deployment, specify the version-overlap behavior.
6. **Check generated artifacts.** Search for generated SDKs, OpenAPI specs, GraphQL schemas, or protobuf definitions that depend on this interface.

### Stop when
- Complete before/after shapes are shown in code blocks
- Every consumer is listed with file:line
- The compatibility matrix has no unresolved cells
- Generated artifacts are accounted for

### Common failures
- **Prose deltas**: "Add a new parameter" without showing the full signature. Fix: Always show complete before and after.
- **Missing consumers**: Checking only direct callers, missing re-exports, generated clients, and test fixtures. Fix: Search for the function name across the entire codebase.
- **Ignoring defaults**: Adding a new parameter without a default breaks existing callers. Fix: Always specify defaults.

---

## Propagation Discovery Protocol

### When to use
Standard and High-Risk plans, any time a function, type, schema, or config key changes.

### Steps

1. **List every changed symbol.** For each CH-n in the plan, name the exact function, class, type, constant, config key, or schema field that changes.
2. **For each changed symbol, search for references:**
   a. Direct callers (grep for the symbol name)
   b. Re-exports (grep for `export`, `__all__`, or module `index` files that re-export it)
   c. Test mocks/fixtures (grep for the symbol in test directories)
   d. Config/schema references (grep for the symbol in YAML, JSON, env, SQL files)
   e. Generated surfaces (grep for the symbol in generated/codegen/proto/graphql directories)
   f. Documentation (grep for the symbol in README, docs, ADR, CONTEXT files)
3. **For each reference found, decide:** Does this reference need to change? Record:
   - `file:line` — symbol reference — CH-n owner — update required: yes/no — reason
4. **Build the propagation map.** Format as:
   ```
   changed_symbol → affected_surface
   - `file:line` — CH-n — update required: yes/no — [reason]
   ```

### Stop when
- Every changed symbol has been searched
- Every reference is accounted for with a yes/no update decision
- Every "update required: yes" has a CH-n owner

### Common failures
- **Forgetting re-exports**: A symbol renamed in its definition file also needs updating in its re-export. Always search index/barrel files.
- **Ignoring test fixtures**: Mocks and fixtures that reference the old shape will break silently. Always search test directories.
- **Missing generated code**: If the symbol appears in a proto, OpenAPI, or GraphQL schema, generated clients will break. Always search generated directories.

---

## Adversarial Thinking Protocol

### When to use
Gate 6 (Attack and Repair) for every plan.

### Steps

1. **Literal execution.** Read the plan as if you are a junior developer who will follow it word-for-word. At each step, ask: "Do I have enough information to write the exact code?" If not, the step is underspecified.
2. **Boundary inputs.** For every input, parameter, and branch in the plan:
   - null / undefined / None
   - empty string / empty array / empty object
   - zero / negative / maximum value
   - invalid type (string where number expected)
   - If the plan does not explicitly handle this, it is a finding.
3. **Caller impact.** For every changed function:
   - Search for every caller
   - Check: does the caller pass the right arguments after the change?
   - Check: does the caller handle the new return type / error type?
4. **State corruption.** If the change involves shared state:
   - What happens if two concurrent operations run?
   - What happens if the operation is retried after partial completion?
   - What happens if the operation is duplicated?
5. **Deployment failure.** If the change involves persisted data or external effects:
   - What happens if the new code is deployed and then rolled back?
   - Can the old code read data written by the new code?
   - Are external effects (API calls, emails, charges) reversible?
6. **Scale.** Would the planned approach work at 10x and 100x current volume? Check for:
   - N+1 queries
   - Unbounded in-memory collections
   - Missing pagination
   - Lock contention

### Classifying findings
- **P0**: Blocks finalization. Data loss, security breach, silent corruption, unrecoverable state.
- **P1**: Must modify the plan. Incorrect behavior, missing error handling, broken caller, missing rollback.
- **P2**: May remain with evidence. Cosmetic, non-blocking performance concern, minor documentation gap.

### Stop when
- Every attack vector has been run or explicitly dismissed with evidence
- Every P0 is resolved
- Every P1 has changed the plan
- Remaining findings are P2 with explicit acceptance rationale

### Common failures
- **Cosmetic findings**: "Consider adding logging" is not an attack. Fix: Every finding must name a concrete scenario, input, and consequence.
- **Attack-without-repair**: Listing risks without modifying the plan. Fix: Every P0/P1 finding must include the exact plan change that resolves it.
- **Missing the forgotten caller**: The most common real bug in plans is a caller that isn't updated after a signature change. Fix: Always grep for every changed function name.

---

## Decision Completeness Check

### When to use
Gate 7 (Validate and Compress) for every plan, before finalization.

### Steps

1. **Scan for deferred language.** Search the plan for:
   - "as needed", "where appropriate", "if applicable", "when suitable"
   - "decide later", "during implementation", "TBD", "TODO"
   - "consider", "might", "probably", "maybe", "could"
   - "the implementer should decide", "choose the appropriate"
   Each occurrence is a deferred decision. Resolve it now or justify why it is genuinely low-impact.
2. **Check every branch.** For every `if/else/switch/match` in pseudocode:
   - Is the else/default case specified?
   - Is the error case specified?
   - Would two implementers write the same code for this branch?
3. **Check every interface.** For every function signature in the plan:
   - Are all parameter types specified?
   - Are defaults specified?
   - Is the return type specified?
   - Are error types specified?
   - Is nullability specified?
4. **Check every test.** For every T-n:
   - Is the exact input specified (not "valid input" — the actual value)?
   - Is the exact expected output specified (not "success" — the actual value)?
   - Is the setup/fixture described?
5. **Verify the implementation ordering.** Can the plan be implemented top-to-bottom?
   - Does step N depend on something introduced in step N+1?
   - Would a developer need to jump back to an earlier step after reading a later one?

### Stop when
- No deferred language remains (or each instance is justified as genuinely low-impact)
- Every branch has an explicit else/error case
- Every interface is fully typed
- Every test has exact input and exact output
- The plan reads top-to-bottom without backtracking

### Common failures
- **"Handle edge cases"**: This is a deferred decision disguised as an instruction. Fix: Name the edge cases and specify how each is handled.
- **"Return appropriate error"**: Which error? What message? What HTTP status? Fix: Specify the exact error type, message, and response code.
- **Backward ordering**: Defining a helper function after the code that calls it. Fix: Order by dependency — foundations first, orchestration last.
