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

Python structured facts use the standard AST. Supported installed Tree-sitter
grammars validate non-Python structure; without a grammar the proof explicitly
falls back to `verified_kind: source`. Use `source` directly when the structured
fields would not improve the plan.
