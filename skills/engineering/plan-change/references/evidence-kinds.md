# Evidence kinds

Every fact requires `kind`, repository-relative `path`, inclusive `lines`, exact
`anchor`, and plan-relevant `claim`. Do not add hashes.

- `source`: no extra fields; verifies the file, range, anchor, and fingerprints.
- `function-signature`: `parameters`, `returns`, `async`.
- `class-signature`: `bases`.
- `call-edge`: `caller`, `callee`.
- `external-call`: `callee`.
- `branch`: `condition`.
- `error`: `error`.
- `side-effect`: `effect`.
- `schema-shape`: `fields`.
- `config-key`: `key`, `value`.
- `generated-from`: `generator`, `output`.
- `directory-ownership`: `directory`.

Python structured facts use the standard AST. Non-Python structured facts
require the matching optional Tree-sitter grammar. If it is unavailable, the
sealer rejects the `F-n` with `fact.structured`; change the declaration to
`kind: source` or install that grammar. Structured declarations never degrade
silently to source proof. Standalone installations retain zero mandatory parser
dependencies.
