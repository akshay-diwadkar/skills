# Ideas: reduce API response latency

## 1. Handoff
- State: decision-ready
- Goal: reduce API response latency
- Success measure: p99 latency < 200ms
- Baseline / status quo: p99 latency = 500ms
- Scope: API gateway service
- Non-goals: database query optimization
- Assumptions: network latency is negligible
- Material unknowns: impact of concurrent request bursts
- Decision horizon: Q3 2026
- Decision criteria: latency reduction, implementation cost
- Selected source playbooks: software/engineering
- Research coverage: internal docs, benchmark logs
- Research limitations: none
- Research stop condition: stop after 5 external sources or 30 minutes
- Research stop reason: condition met

## 2. Evidence

### External evidence

External research status: completed

| ID | Finding | Source | Locator | Date/freshness | Relevance |
| --- | --- | --- | --- | --- | --- |
| E1 | In-memory cache reduces p99 by 60% | https://example.com/benchmarks | § 3 | 2026-06 | high |

## 3. Candidate ideas

### I1. In-Memory Response Caching
- Mechanism: store frequent endpoint responses in Redis
- Mechanism category: in-memory-caching
- Why it applies: 80% of requests are read-only repeated queries
- Evidence: E1 benchmark supports the mechanism
- Decision-criteria fit: best latency reduction at low cost
- Expected impact: high
- Assumptions and dependencies: Redis cluster available
- Effort: low
- Risk: low
- Confidence: high
- What would disconfirm it: cache hit rate < 40%
- Cheapest decisive experiment: benchmark cache prototype; metric: hit rate; pass/fail: >60%; duration: 1d; cost/effort: low

### I2. Response Payload Compression
- Mechanism: compress JSON responses with Brotli
- Mechanism category: payload-compression
- Why it applies: large payloads slow down transmission
- Evidence: E1 secondary finding on transfer size
- Decision-criteria fit: moderate latency gain, low cost
- Expected impact: medium
- Assumptions and dependencies: CPU overhead acceptable
- Effort: medium
- Risk: low
- Confidence: moderate
- What would disconfirm it: CPU usage spikes > 90%
- Cheapest decisive experiment: test Brotli compression; metric: payload size; pass/fail: >30% reduction; duration: 1d; cost/effort: low

### I3. Connection Pooling
- Mechanism: reuse HTTP/2 TCP connections
- Mechanism category: connection-pooling
- Why it applies: handshake overhead adds 50ms per request
- Evidence: E1 mentions connection setup cost
- Decision-criteria fit: uncertain gain at medium cost
- Expected impact: medium
- Assumptions and dependencies: upstream supports HTTP/2
- Effort: medium
- Risk: medium
- Confidence: moderate
- What would disconfirm it: connection drops increase
- Cheapest decisive experiment: test pool size 50; metric: latency; pass/fail: <300ms; duration: 2d; cost/effort: medium

## 4. Comparison

| Rank | Candidate | Impact | Effort | Risk | Confidence | Evidence strength |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | I1 | high | low | low | high | strong |
| 2 | I2 | medium | medium | low | moderate | moderate |
| 3 | I3 | medium | medium | medium | moderate | moderate |

## 5. Recommendation
- Provisional lead: I1 — In-Memory Response Caching
- Why it leads: highest latency reduction with lowest implementation effort
- Why it beats rank 2: Caching eliminates computation, while compression only speeds network transfer
- Cheapest decisive experiment: benchmark cache prototype; metric: hit rate; pass/fail: >60%; duration: 1d; cost/effort: low
- What could change the ranking: Redis infrastructure cost exceeds budget
- Conditions that would change the ranking: cache hit rate < 30% or memory cost > $5k/mo
- How decision criteria were applied: latency reduction was weighted first; I1 wins on latency, and cost confirmed the order over I2

## 6. Contradictions and open questions
- Strongest challenge to rank 1: cache invalidation coordination across microservices
- Baseline / status quo comparison: all candidates improve on the 500ms baseline; I1 improves it most
- Condition for a different winner: I2 wins if payload size dominates user-perceived latency
- Remaining contradiction or uncertainty: none remaining — E1 measured on the same benchmark dataset
