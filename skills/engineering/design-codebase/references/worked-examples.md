# Design Handoff: Isolate Payment Provider Semantics

## Evidence Ledger

- [E-1] source: request | locator: user-request | claim: Provider-specific request and failure behavior should stop leaking into checkout and subscription callers.
- [E-2] source: code | locator: payments/service.py:1-7 | anchor: charge_payment | sha256: 383f9a66d5763c7a293a22f6388a418a7fba3f8979b35aa7c31fb404d0372c19 | claim: The payment service constructs provider SDK requests and exposes provider exceptions directly.
- [E-3] source: code | locator: checkout/process.py:1-6 | anchor: checkout | sha256: dcf982001e19cb93ac5b5bbf888233b985f8a933b53623ad2f71b3f1153f7e0d | claim: Checkout supplies provider-specific optional values and handles provider timeout types.
- [E-4] source: test | locator: tests/test_checkout.py:1-6 | anchor: test_checkout_decline | sha256: e5315c9858912d0b35c027fc7f9927dcb1cd0f266bc29b7f6d2d10cf3ac69e29 | claim: Current tests assert provider-specific decline exceptions at a domain call site.

## Problem & Scope

Checkout and subscription behavior depend on provider request fields and
provider exception classes, so an SDK change propagates beyond the integration
owner. The design covers the synchronous charge contract and its caller-visible
failures; settlement workflows and provider selection policy are outside this
decision. [E-1] [E-2] [E-3]

## Chosen Design & Depth Rationale

- Boundary: Domain payment operations to provider integration
- Owner: Payments integration
- Core abstraction: PaymentGateway protocol using ChargeRequest, PaymentResult, and domain payment errors
- Design: Callers submit a domain-owned `ChargeRequest` to `PaymentGateway.charge`; the integration owner translates provider requests, results, and exceptions.
- Hidden details: Provider SDK request construction, response types, exception taxonomy, and timeout exception classes
- Exposed controls: Charge amount, currency, payment token, and optional idempotency key
- Depth rationale: One charge operation and three domain types hide four provider concepts already used by independent callers, while callers retain every control that changes payment behavior. This has a higher functionality-to-interface ratio than exposing the SDK request and exception families directly. [E-2] [E-4]

## Alternatives Considered

### Alternative: Consolidate orchestration and provider calls

- Boundary: Checkout and subscription flows call concrete functions owned by the payment service module
- Owner: Payment service
- Core abstraction: Concrete payment-service module functions over provider SDK values
- Rejected because: Moving all callers behind concrete module functions would centralize code but also give the payment service ownership of checkout and subscription orchestration. The pieces share provider translation, not domain workflow ownership, so consolidation would create a broader and less coherent boundary. [E-2] [E-3]

## Target Interface Contract

| Contract aspect | Today | Proposed | Evidence |
|---|---|---|---|
| Signature | `provider_sdk.charge(amount, currency, token=None) -> ProviderResponse` | `PaymentGateway.charge(request: ChargeRequest) -> PaymentResult` | [E-2] |
| Defaults | `token=None`; SDK timeout is implicit | `ChargeRequest.idempotency_key=None`; gateway timeout policy is integration-owned | [E-2] [E-3] |
| Nullability | Token and provider response fields may be null | Payment token and idempotency key are optional; `PaymentResult` is non-null | [E-2] |
| Caller-visible errors | `ProviderDeclined`, `ProviderTimeout`, and other SDK exceptions | `PaymentDeclined` and `PaymentUnavailable` | [E-3] [E-4] |

- Error surface direction: shrink
- Error surface justification: Callers handle two stable domain outcomes instead of the provider exception family; provider-specific distinctions remain observable inside the integration boundary. [E-2] [E-4]

## Generality Justification

The design covers two distinct present-day use patterns: checkout performs an
immediate customer charge, while subscriptions initiate recurring charges with
an idempotency key. Both need the same stable charge result and failure
semantics despite different orchestration. If a third pattern required
authorization without capture, the contract would add a distinct operation or
request variant rather than expose provider SDK types. [E-2] [E-3]

## Consolidation Considered

Consolidating checkout, subscription, and provider translation into the payment
service was evaluated because the current code changes together around provider
updates. It was rejected: provider translation is tightly coupled, but checkout
and subscription policy have different owners and lifecycles. The chosen
boundary consolidates only translation and error mapping. [E-2] [E-3]

## Documentation Obligations

Callers must know that the gateway owns provider timeout policy and error
translation, that an idempotency key identifies one logical charge attempt, and
that `PaymentUnavailable` does not prove the provider declined the charge.
These semantics are not fully expressed by the signature and must be scheduled
by `plan-change` as contract documentation. [E-2] [E-3]

## Open Questions for the Planner

The design is complete. During grounding, the planner must reconcile the full
caller inventory and identify which existing characterization tests own the
provider-to-domain error mapping; those are implementation-scope questions, not
design choices. [E-3] [E-4]
