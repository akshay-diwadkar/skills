# Changelog

## 3.3.0 - 2026-08-05

- Accept sealed plan-contract v7 plans while retaining an isolated frozen v6
  compatibility reader for historical sealed plans.
- Surface deterministic topological `CH` order from `depends_on` during intake
  and scaffolding so implementation follows the declared change graph.
