# Explicit invocation policy

This minor release classifies every skill as user-invoked, model-invoked, or
both and certifies that policy for Claude Code, Codex, and GitHub Copilot.
Implementation, publication, external-write, and external-output workflows are
blocked from implicit activation, while lightweight read-only routing and
codebase mapping remain available to the model.

Repository validation now checks the neutral policy registry, provider
adapters, real skill references, and authority-sensitive capabilities.
Skills CLI 1.5.21 installation coverage verifies the complete collection and
each individual skill on every certified platform.
