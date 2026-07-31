# Progressive-disclosure skill interfaces

This patch release refactors every top-level skill file into a concise operating
interface while preserving invocation, authority, validation, finalization, and
artifact contracts. Phase-specific protocols and edge cases now live behind
direct references surfaced by the common CLI.

Repository validation now rejects broken or orphaned skill references, verifies
that mandatory rules remain discoverable through `required_reads`, and checks a
vendored-tokenizer report showing a 62.65% reduction in initial skill tokens.
