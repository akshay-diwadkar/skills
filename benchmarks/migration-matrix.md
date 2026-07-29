# Benchmark Migration Matrix

The domains below are frozen for the next portfolio versions. Migration must
add outcome-specific oracles and fair baselines rather than reuse
`map-codebase` retrieval metrics.

| Skill | Frozen domain | Next oracle and comparison | Current evidence |
| --- | --- | --- | --- |
| `plan-change` | Order fulfilment | Semantic owner and propagation scoring; constrained plan-to-implementation simulation | Small parser/safety cases; material keyword scoring |
| `implement-plan` | Developer CLI with plugins | Behavioral migration, hidden callers, dirty worktree, rollback, external-effect refusal | Repositories of at most five files |
| `audit-codebase` | Tenant authentication | Independent injected-defect manifests, clean controls, precision/recall, deduplication, severity calibration | 8- and 18-file cases; material keyword scoring |
| `optimize-codebase` | Ingestion pipeline | Executable algorithmic, I/O, database, and memory benchmarks with warm-up, repeated samples, dispersion, parity, rollback | One- to four-file static cases |
| `design-codebase` | Event-driven notifications | Structural alternatives, dependency direction, compatibility, downstream `plan-change` validity | No tracked evaluation portfolio |
| Remaining skills | Outcome-specific frozen domain per migration | Outcome-specific oracle and independent fair baseline | Regression or contract evidence only |

Each migrated fixture must use the shared manifest lifecycle, external ground
truth, deterministic regeneration where synthetic, protected-path checks, and
an explicit statement of limitations.
