# Manual Bundle Contract

Use `contract_version: manualize-1`. Validate the bundle with `schemas/manual-bundle.schema.json`.

The bundle is the deterministic bridge between sources and the manual:

- `operation` prevents an audit bundle from receiving a write receipt.
- `profile` and `glossary` drive language validation during finalization.
- `sources` bind repository-relative source bytes with SHA-256.
- `required_facts` bind exact canonical claims to source identifiers.
- `integrity_literals` preserve exact commands, paths, and values.
- `procedures` define marker order.
- `warnings` bind warning text to the hazardous action that must follow it.
- `recovery_steps`, `prerequisites`, and `branches` define operational completeness.
- Optional `section` values restrict a check to an exact Markdown heading.

Use lowercase hexadecimal hashes without the `sha256:` prefix for source records. The finalizer uses the prefix in its receipt.

Keep the glossary inline so finalization needs only the manual and bundle. For direct language-parser use, write the same glossary object to a standalone JSON file.

The finalizer replaces any prior receipt only after both validators pass. Its `bundle_hash` covers canonical JSON for the complete bundle with `validation_receipt` removed.
