# Deploy the service
<!-- plan-contract: 2 -->
<!-- tier: high-risk; task-type: external-integration -->

## Outcome and Scope
- SC-1: Service is deployed.
- In scope: `src/deploy.py` and production deployment.
- Unchanged: Production data.

## Evidence Ledger
- F-1: `src/deploy.py:1` | anchor: `deploy` | observation: Deployment calls an external system.

## Decisions
- D-1: selected: run deploy | because: F-1 | rejected: local simulation.

## Implementation Specification
- CH-1: `src/deploy.py` | anchor: `deploy` | status: existing | change: Execute production deployment.

## Traceability
- C-1: Production data is preserved | status: at-risk
| Criterion / constraint | Changes | Tests | Status / rollback |
|---|---|---|---|
| SC-1 | CH-1 | T-1 | Stop without authorization. |
| C-1 | CH-1 | T-1 | Verify no external call. |

## Verification
- T-1: given: production target | expect: deployed service | command: `python src/deploy.py production`

## Risks, Assumptions, and Attack
- Assumptions: Credentials exist.
- A1: not-applicable | evidence: One entry point.
- A2: repaired | evidence: Authorization gate.
- A3: repaired | evidence: High-Risk classification.
- A4: not-applicable | evidence: Serialized deployment.
- A5: repaired | evidence: Rollback section.
- A6: repaired | evidence: Stop condition.
- R-1 P1: External production mutation | Resolution: CH-1/T-1

## Compatibility and Rollout
Deploy one version, monitor health, and stop on errors.

## Durable Rollback
Redeploy the prior artifact; no irreversible data changes are authorized.
