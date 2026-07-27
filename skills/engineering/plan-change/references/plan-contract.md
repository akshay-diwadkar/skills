# Plan contract v5

`plan-contract.json` is the sole editable contract source. Generated
`plan_contract_data.py` modules carry that data into standalone skills;
`plan_runtime.py` implements validation behavior against generated data.
Repository validation fails when generated data or synchronized runtimes diverge.
Only one v5 marker and metadata object are allowed. Facts are typed, fingerprinted
repository evidence. The finalizer creates targeted bindings for evidence and
existing change targets; unrelated changes are permitted when those bindings remain
current. The receipt binds the exact plan body and binding JSON.

Both classification passes record `tier_signals`. Any transitive consumer, shared
internal interface, uncertain root cause, multiple architectural layers,
sync-plus-async consumers, or multiple test surfaces requires at least `standard`.
`tiny` requires one existing `local-production`, `reversible` change.

Every final domain retains a complete obligation matrix. A satisfied obligation owns
decision, change, and concept-specific test references. A `not-applicable` obligation
instead owns a concrete `reason` and `F-n` evidence proving absence; contradictory
facts, changes, blueprints, tests, or domain claims fail validation.

Use `prepare_plan.py` to create the baseline, inventory, and draft in isolated
storage. `check_plan.py` and `finalize_plan.py` require both the baseline and
inventory. Every inventory candidate must be grounded by an `F-n` and reconciled
through a matching `P-n` disposition or owning `CH-n`; the v5 markdown record
schema is intentionally breaking within the v5 release wave; regenerate older v5
plans rather than translating them.

## Structural fact language support

The JavaScript, TypeScript, and Kotlin support below is additive within contract
v5. It changes neither record syntax nor fact fields. Every fact in every
language still requires a current repository-relative path, inclusive line
range, anchor text, excerpt SHA-256, and file SHA-256. `grounding` means those
universal checks apply but the language structure is not additionally parsed.

| Fact kind | Python | JavaScript / JSX | TypeScript / TSX | Kotlin | Other languages |
|---|---|---|---|---|---|
| `function-signature` | AST | tree-sitter | tree-sitter | tree-sitter | grounding |
| `class-signature` | AST | tree-sitter | tree-sitter | tree-sitter | grounding |
| `call-edge` | AST | tree-sitter | tree-sitter | tree-sitter | grounding |
| `external-call` | AST | tree-sitter | tree-sitter | tree-sitter | grounding |
| `branch` | AST | tree-sitter | tree-sitter | tree-sitter | grounding |
| `error` | AST | tree-sitter | tree-sitter | tree-sitter | grounding |
| `side-effect` | AST | tree-sitter | tree-sitter | tree-sitter | grounding |
| `schema-shape` | annotated class AST | grounding | grounding | grounding | JSON properties or grounding |
| `config-key` | config parser checks | config parser checks | config parser checks | config parser checks | JSON/TOML/INI/CFG/YAML checks or grounding |
| `generated-from` | repository relationship | repository relationship | repository relationship | repository relationship | repository relationship |
| `directory-ownership` | filesystem relationship | filesystem relationship | filesystem relationship | filesystem relationship | filesystem relationship |
| `authorization-boundary` | grounding | grounding | grounding | grounding | grounding |
| `transaction-boundary` | grounding | grounding | grounding | grounding | grounding |
| `test-behavior` | grounding | grounding | grounding | grounding | grounding |
| `documentation-contract` | grounding | grounding | grounding | grounding | grounding |

For JS/TS signatures, `parameters` is the normalized text inside the
parentheses, `returns` omits the leading colon, and a missing annotation is
`unannotated`. Kotlin uses the same convention and maps `suspend` to
`async: true`. JS/TS `bases` is the normalized `extends`/`implements` clause;
Kotlin `bases` is the normalized delegation-specifier list. A missing pinned
parser dependency or a false structural claim blocks validation. A genuinely
unsupported language/kind combination never creates a language-only failure;
its hash and anchor proof remains mandatory.
