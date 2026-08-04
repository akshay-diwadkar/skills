# Design Handoff: Cache Boundary

## Decision
D-1: selected: introduce a repository cache facade | rejected: inline caching | drawback: facade adds indirection.

## Surfaces
- Cache invalidation must reach every repository caller.
- The facade delegates reads to the existing store.
