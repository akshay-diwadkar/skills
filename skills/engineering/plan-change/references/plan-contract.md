# Plan contract v4

`plan-contract.json` is authoritative. A plan has exactly one v4 marker, strict JSON `plan-metadata` with provisional and final classification, a finalizer-owned `plan-repository` binding, and one v4 receipt. Facts fingerprint a cited line range and file; receipts bind plan bytes plus repository identity, revision, dirty state, and target tree hash.

This detects accidental edits and stale repository facts. It is not protection against a malicious local actor who can rewrite the plan, binding, and repository together. Older plans fail with an unsupported-contract diagnostic and are never converted.
