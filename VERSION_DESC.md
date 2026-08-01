# Agent-first runtime migration

This breaking release makes `map-codebase` the sole scripted discovery skill.
All other runtimes take agent-selected artifacts and cited paths, seal once,
and never classify or inventory an unrelated repository. Deprecated v5 plan
readers and multi-phase classifier lifecycles are removed.
