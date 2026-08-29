# HTTP and APIs — Senior

> **Topic:** [HTTP and APIs](../README.md)
> **Focus:** Load shedding and backpressure, circuit breakers, request-scoped deadlines propagated across a call chain, connection pool sizing under real load, and API versioning/compatibility.

---

## Introduction

At scale, an API doesn't just need to handle requests correctly — it needs to survive its dependencies failing, its own capacity being exceeded, and years of evolution without breaking existing clients. This level connects HTTP mechanics to systems-level resilience patterns.

---

## Prerequisites

- Comfortable with graceful shutdown, connection pooling, and retry-with-backoff (middle level).

---

## Core Concepts

### 1. Load shedding: reject early, don't degrade slowly

```go
sem := make(chan struct{}, maxConcurrent)
func middleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        select {
        case sem <- struct{}{}:
            defer func() { <-sem }()
            next.ServeHTTP(w, r)
        default:
            http.Error(w, "server busy", http.StatusServiceUnavailable)
        }
    })
}
```

Once a service is at capacity, accepting more requests and letting them queue behind an overloaded resource degrades *every* request's latency, including ones that would otherwise succeed quickly. Rejecting immediately with `503` past a concurrency limit keeps latency bounded for accepted requests and gives clients a clear signal to back off.

### 2. Circuit breakers stop calling a failing dependency

A circuit breaker tracks a downstream dependency's failure rate; once it crosses a threshold, the breaker "opens" and fails fast (without even attempting the call) for a cooldown period, then allows a trial request to test recovery ("half-open"). This prevents a struggling downstream from being further overwhelmed by continued traffic, and prevents your own service from burning resources (goroutines, connections) on calls that are very likely to fail or time out anyway.

```go
if !breaker.Allow() {
    return ErrCircuitOpen // fail fast, no network call attempted
}
err := callDownstream()
breaker.Record(err)
```

### 3. Propagate one deadline across the entire call chain

```go
ctx, cancel := context.WithTimeout(r.Context(), 3*time.Second)
defer cancel()
// every downstream call — DB, cache, another service — uses this SAME ctx
```

A request budget of 3 seconds means every downstream call shares that budget, not each getting its own independent 3 seconds. Without this, a chain of 3 sequential downstream calls, each with its own "generous" 5-second timeout, can make a single request take 15 seconds before ultimately failing anyway.

### 4. Connection pool sizing is a capacity-planning exercise, not a guess

`MaxIdleConnsPerHost` (client) and a database driver's `MaxOpenConns` should be sized based on measured concurrency needs and the downstream's own capacity — too small causes queuing/latency under load; too large can overwhelm a downstream service or exhaust file descriptors on your own host. Load testing at expected peak traffic is the only reliable way to size these correctly.

### 5. API versioning is a compatibility promise, not a formality

Whether via URL path (`/v1/users`), a header, or content negotiation, a versioning strategy exists to let you evolve the API without breaking existing clients on their own schedule. The senior-level discipline is treating a "minor" change (adding a required field, changing a field's type, tightening validation) with the same rigor as a major one if it can break an existing client's assumptions — additive, optional changes are safe; anything else needs a new version or a deprecation window.

---

## Worked Example — A Cascading Timeout Traced to Independent Per-Call Deadlines

A request handler called three downstream services sequentially, each wrapped in its own `context.WithTimeout(context.Background(), 5*time.Second)` — using `context.Background()` instead of deriving from the incoming request's context. Under a partial outage where the first downstream call was slow (taking the full 5 seconds before failing), the request still proceeded to attempt the second and third calls with their own fresh 5-second budgets, producing a 15-second total latency and a confusing "why didn't this time out sooner" investigation. The fix: derive every downstream call's context from `r.Context()` with a single top-level deadline, so a slow first call's time consumption is reflected in the budget remaining for subsequent calls.

---

## Pros & Cons

| Pattern | Pros | Cons |
|---|---|---|
| Load shedding | Bounded latency for accepted requests under overload | Rejected clients need a well-defined retry/backoff response themselves |
| Circuit breaker | Prevents wasted calls to a known-failing dependency | Adds state and tuning (thresholds, cooldown); a misconfigured breaker can open too eagerly |
| Single propagated deadline | Predictable total request latency | Requires discipline — every downstream call site must derive from the same context |

---

## Best Practices

1. Set a concurrency limit and shed load with `503` past it, rather than letting requests queue unboundedly.
2. Wrap dependencies prone to cascading failure with a circuit breaker.
3. Derive every downstream call's context from the incoming request's context with one top-level deadline — never `context.Background()` mid-chain.
4. Size connection pools from load-test data, not defaults or guesses.
5. Treat any API change that could break an existing client's assumptions as requiring versioning or a deprecation window.

---

## Edge Cases & Pitfalls

- **A circuit breaker with too aggressive a threshold** can open on normal, brief error-rate noise, needlessly failing fast when the dependency was actually fine.
- **Load shedding without communicating retry guidance** (a `Retry-After` header) leaves clients guessing when to retry, often making them retry immediately and worsen the overload.
- **A "minor" API field-type change** that looks harmless in isolation can break a strongly-typed client's deserialization — review every change against the versioning policy, not just intuition.

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| Using `context.Background()` for downstream calls instead of deriving from `r.Context()` | Always derive from the incoming request's context |
| No load-shedding limit — requests queue until the process falls over | Set a concurrency limit, reject with `503` past it |
| Treating every API change as automatically backward-compatible | Review against an explicit compatibility policy |

---

## Common Misconceptions

> *"A circuit breaker replaces the need for timeouts."* — No, they're complementary: timeouts bound a single call's duration; a circuit breaker stops making calls at all once a dependency is known to be failing.

---

## Cheat Sheet

```
Load shedding    → concurrency limit + fast 503, don't queue unboundedly
Circuit breaker  → fail fast on a known-failing dependency, retry-probe periodically
One deadline     → derive every downstream ctx from r.Context(), never Background() mid-chain
Pool sizing      → from load-test data, not defaults
```

---

## Summary

- Shed load explicitly (reject with `503` past a concurrency limit) rather than letting requests queue unboundedly under overload.
- Circuit breakers stop wasting resources on calls to a known-failing dependency.
- Propagate a single deadline from the incoming request through every downstream call — never start a fresh, independent timeout mid-chain.
- Size connection pools from real load-test data.
- Treat API compatibility as an explicit policy, not an assumption.

---

## Further Reading

- Google SRE Book — *Addressing Cascading Failures*: <https://sre.google/sre-book/addressing-cascading-failures/>
- `sony/gobreaker` (a widely-used Go circuit breaker): <https://github.com/sony/gobreaker>

---

## Related Topics

- [Database and Distributed Systems — Senior](../06-database-and-distributed-systems/senior.md) — partial failure handling in depth.
- [Production Debugging — Senior](../07-production-debugging/senior.md)

---

## Check your understanding

1. Explain HTTP and APIs — Senior Level in your own words and name the problem it solves.
2. How would you apply the ideas around Introduction, Prerequisites, Core Concepts in a realistic engineering change?
3. What failure mode or misuse should you look for, and what evidence would reveal it?
4. How would you validate a system-level decision about HTTP and APIs — Senior Level under uncertainty?
5. What observable result would convince you that the approach improved the system?
