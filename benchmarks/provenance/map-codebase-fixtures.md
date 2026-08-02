# Map-codebase fixture provenance

All fixtures are original, local, deterministic source. They reproduce only
architectural pressures observed in public repositories; no upstream code or
runtime download is used.

| Fixture | Structural inspiration |
| --- | --- |
| `schema-migration-service` | Kubernetes-style module/API boundary pressure, adapted to an original billing, migration, and event-outbox service. |
| `plugin-workspace` | [Backstage plugin workspaces](https://github.com/backstage/backstage/tree/master/plugins): package ownership and frontend/backend boundaries. |
| `component-pipeline` | [OpenTelemetry Collector components](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/docs/new-components.md): metadata, component families, and generated distribution surfaces. |
| `resolver-scale-stress` | The former repository-owned patterned SignalForge workload, retained unchanged for bounded-candidate latency measurements only. |

The three utility fixtures are explicit, behavior-tested project blueprints;
dependency locks and toolchain inputs make native builds reproducible without
copying upstream runtime code. The scale fixture is intentionally patterned and
is not used to support resolver quality or reliability claims.
