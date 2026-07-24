# Worked Examples

Use these examples as calibration, not templates to copy. Each shows how evidence, change level, pattern cost, technical debt, migration, operational semantics, and validation receipts shape Contract v2 assessments.

## Contents

1. Reject Strategy for a stable two-branch decision (L1)
2. Introduce an Adapter around a volatile SDK (L2)

---

## 1. Reject Strategy for a Stable Two-Branch Decision

# Assessment: Invoice Output Formatter Structure
<!-- design-assessment-contract: 2; level: L1 -->

## Decision Summary
- Invocation mode: targeted
- Selected target: `billing/formatter.py`
- Selected level: L1
- Recommended design: Reject Strategy pattern. Retain direct exhaustive branch in `billing/formatter.py` with local function extraction.
- Why minimum sufficient: L0 is insufficient because rendering logic needs local function decomposition; L2/Strategy adds 4 unevidenced concepts without reducing cross-module change propagation.
- Protected behavior and contracts: C-1 preserved (CLI output format and error bytes).
- Primary structural pressure: P-1 (local readability of rendering logic).
- Technical-debt disposition: TD-1 disposition: accept | boundary: local
- Residual risk: R-1 low
- Next owner: finish assessment

## Scope and Protected Contracts
- C-1: status: preserved | contract: `billing/formatter.py:render_invoice` output bytes and error types | authorization: none
- H-1: status: assessment-only | next: finish assessment
- TD-1: type: structural | evidence: F-1 | principal: monolithic formatting function body | interest: minor cognitive overhead | frequency: current | blast-radius: billing/formatter.py | disposition: accept | reason: repayment cost of Strategy pattern exceeds interest | repayment-boundary: local | recurrence-guard: none | revisit-trigger: adding third format provider

## Evidence and Current State
- F-1: `billing/formatter.py:12` | anchor: `def render_invoice` | observation: Output choice is a closed enum with two variants used in one module | source: code | strength: direct | freshness: current
- F-2: `tests/test_formatter.py:45` | anchor: `def test_compact_and_detailed` | observation: Characterization tests verify exact output bytes for both variants | source: test | strength: direct | freshness: current
- Current flow: CLI input -> `render_invoice` -> enum branch -> compact/detailed string -> output bytes.

## Design Pressures and Classification
- P-1: rank: 1 | evidence: F-1 | pressure: Local function body is long, but choice has zero external volatility or substitution requirement.
- D-1: level: L1 | design-id: formatter-local-simplification | selected: local simplification via helper functions in billing/formatter.py | because: F-1, F-2, P-1 | rejected: L2 Strategy pattern adds 4 classes and a factory without evidence.

## Alternatives and Pattern Decisions
- O-1: level: L0 | design-id: formatter-no-op | selected: no | concepts: none | argument-for: zero edits | argument-against: leaves 120-line function intact | revisit: none
- O-2: level: L1 | design-id: formatter-local-simplification | selected: yes | concepts: local helper functions | argument-for: keeps zero cross-module indirection | argument-against: keeps enum dispatch | revisit: adding third format
- O-3: level: L2 | design-id: formatter-strategy | selected: no | concepts: FormatterStrategy, CompactFormatter, DetailedFormatter, FormatterFactory | argument-for: satisfies design pattern textbook | argument-against: 4 new classes for 2 stable variants | revisit: third format externally owned

## Local Simplification and Preservation
- Responsibility: `billing/formatter.py` owns invoice rendering.
- Concepts removed: none
- Concepts retained: `render_invoice` function and Enum variants.
- Preservation proof: C-1 and V-1.

## Verification and Residual Risk
- V-1: proves: D-1 | method: `pytest tests/test_formatter.py` | expected: 100% pass on exact byte assertions.
- R-1: severity: low | scenario: future third format added | consequence: revisit design level | owner: maintainer | follow-up: monitor PR requests

---

## 2. Introduce an Adapter Around a Volatile SDK

# Assessment: Payment Provider SDK Integration Boundary
<!-- design-assessment-contract: 2; level: L2 -->

## Decision Summary
- Invocation mode: targeted
- Selected target: `payments/adapter.py`
- Selected level: L2
- Recommended design: Introduce narrow `PaymentGateway` interface and provider `Adapter` in `payments/adapter.py`.
- Why minimum sufficient: L1 is insufficient because 4 domain modules directly import volatile SDK and edit in lockstep on SDK updates; L3 is unnecessary as no cross-system state migration is needed.
- Protected behavior and contracts: C-1 preserved (payment authorization API signatures).
- Primary structural pressure: P-1 (external SDK volatility propagating to 4 domain modules).
- Technical-debt disposition: TD-1 disposition: repay | boundary: L2 boundary redesign
- Residual risk: R-1 low
- Next owner: plan-with-senior-dev

## Scope and Protected Contracts
- C-1: status: preserved | contract: `payments/service.py` payment processing signature | authorization: none
- H-1: status: assessment-only | next: plan-with-senior-dev
- TD-1: type: boundary | evidence: F-1, F-2 | principal: direct SDK coupling in domain callers | interest: 3 recent SDK upgrades forced edits across 4 modules | frequency: recurring | blast-radius: payments, orders, subscriptions, checkout | disposition: repay | reason: Adapter isolates SDK field renames to 1 file | repayment-boundary: L2 boundary redesign | recurrence-guard: lint rule blocking direct SDK imports outside payments/adapter.py | revisit-trigger: none

## Evidence and Current State
- F-1: `payments/service.py:34` | anchor: `import provider_sdk` | observation: 4 domain modules construct provider SDK requests directly | source: code | strength: direct | freshness: current
- F-2: `git-history:3a2f1b70298d5c4e90218175f7396781f8084a91:payments/service.py:34` | anchor: `import provider_sdk` | observation: 3 recent provider SDK releases forced edits across 4 modules | source: repository-history | strength: corroborated | freshness: current
- Current flow: Domain caller -> Direct SDK constructor -> Network call -> SDK Exception.

## Design Pressures and Classification
- P-1: rank: 1 | evidence: F-1, F-2 | pressure: SDK field renames and exception types leak into domain logic across 4 independent modules.
- D-1: level: L2 | design-id: payment-gateway-adapter | selected: PaymentGateway interface and Adapter implementation | because: F-1, F-2, P-1 | rejected: L1 local edits do not prevent cross-module change propagation.

## Alternatives and Pattern Decisions
- O-1: level: L0 | design-id: payment-sdk-direct | selected: no | concepts: none | argument-for: no new files | argument-against: SDK updates continue breaking 4 modules | revisit: none
- O-2: level: L1 | design-id: payment-sdk-helper | selected: no | concepts: shared helper function | argument-for: simple | argument-against: leaves direct SDK dependencies in caller imports | revisit: none
- O-3: level: L2 | design-id: payment-gateway-adapter | selected: yes | concepts: PaymentGateway interface, ProviderAdapter | argument-for: isolates SDK to 1 module | argument-against: 1 new interface file | revisit: provider deprecation

### G-1: Adapter — admit
- Scope: introduced | Result: admit | Evidence: F-1, F-2, P-1

| Gate | Answer | Evidence | Consequence |
|---|---|---|---|
| Q1 | yes | F-1, P-1 | Resolves SDK change propagation |
| Q2 | yes | F-1, F-2 | 3 SDK updates forced edits in 4 modules |
| Q3 | yes | F-1, P-1 | L1 helper functions leave SDK imports leaky |
| Q4 | yes | F-1, P-1 | Single owner payments/adapter.py |
| Q5 | yes | F-1, P-1 | Stable PaymentGateway interface |
| Q6 | yes | F-1, P-1 | Reduces cross-module edits |
| Q7 | yes | F-1, P-1 | Constrains SDK dependency |
| Q8 | yes | F-1, P-1 | Payment status state unambiguous |
| Q9 | yes | F-1, P-1 | C-1 preserved |
| Q10 | yes | F-1, F-2 | Characterization tests pass |
| Q11 | yes | F-1, P-1 | Operational semantics explicit |
| Q12 | yes | F-1, P-1 | Python interface/adapter idiom |
| Q13 | yes | F-1, P-1 | Reversible in 2 PRs |
| Q14 | yes | F-1, F-2 | Net value exceeds cost |

## Target Boundary
- Responsibility and owner: `payments/adapter.py` owns SDK lifecycle and translation.
- Dependency direction: domain policy -> `PaymentGateway` port -> `ProviderAdapter` -> SDK.
- State and contract ownership: domain owns `PaymentResult` value object.
- Allowed calls and failures: authorize, capture, refund; raises `PaymentProviderError`.

## Migration and Rollback
- M-1: prerequisite: characterize current SDK responses | changed boundary: payment gateway | preserved: C-1 | proof: V-1 | rollback trigger: payload mismatch or latency spike | rollback action: repoint caller to direct SDK implementation | cleanup: remove direct SDK imports after 1 release cycle

## Operational Semantics
- Source of truth: provider API response.
- Failures: mapped to PaymentProviderError.
- Timeouts: 5000ms deadline passed to SDK.
- Retries: 2 retries with exponential backoff on 5xx errors.
- Idempotency: idempotency key generated per request ID.
- Ordering: not-applicable | evidence: F-1 | reason: Single payment requests are stateless.
- Transactions: not-applicable | evidence: F-1 | reason: Single payment requests have no local database transaction.
- Observability: log provider request ID and status code.
- Resource limits: max 50 concurrent HTTP connections.

## Verification and Residual Risk
- V-1: proves: D-1 | method: `pytest tests/test_payments.py` | expected: Adapter correctly translates success and error payloads.
- R-1: severity: low | scenario: SDK adds new error code | consequence: update adapter mapping | owner: payments team | follow-up: monitor error logs
