# HTTP and APIs — Interview Prep

> **Topic:** [HTTP and APIs](../README.md)

---

## Conceptual / Foundational

**Q: What's wrong with `http.ListenAndServe(":8080", nil)` in production?**
A: No timeouts are configured — a slow or malicious client can hold a connection open indefinitely, exhausting server resources. Use an `http.Server` with explicit `ReadTimeout`/`WriteTimeout`/`IdleTimeout`.

**Q: Why must you close `resp.Body`?**
A: The response body holds the underlying TCP connection open until fully read and closed; forgetting to close it leaks connections and eventually exhausts the client's connection pool.

**Q: What does `http.Server.Shutdown` do differently from just killing the process?**
A: It stops accepting new connections immediately but waits (up to a context deadline you provide) for in-flight requests to finish, enabling zero-downtime deploys.

## Tricky / Trap Questions

**Q: You create a new `http.Client{}` for every outgoing request. What's the hidden cost?**
A: It defeats connection pooling/reuse — every request pays for a fresh TCP (and TLS) handshake instead of reusing a keep-alive connection, which is a significant, often invisible, latency and resource cost under load.

**Q: A request chain calls three downstream services, each with its own independent `context.WithTimeout(context.Background(), 5s)`. Why is this a problem?**
A: Each call gets its own fresh 5-second budget instead of sharing the request's overall deadline — a slow first call doesn't reduce the time budget for the next ones, so total latency can balloon (up to 15s here) before ultimately failing anyway. Fix: derive every downstream context from the incoming request's context with one top-level deadline.

**Q: Is it safe to blindly retry a failed `POST` request?**
A: No — `POST` isn't guaranteed idempotent; a naive retry can create a duplicate resource. Only retry idempotent methods (or use an idempotency key) automatically.

## System / Design Scenarios

**Q: Design load-shedding for a service approaching capacity.**
A: A bounded semaphore (or equivalent concurrency limiter) around request handling; once full, immediately return `503` (with a `Retry-After` header) instead of letting requests queue and degrading everyone's latency.

**Q: How would you protect a service from a downstream dependency that's failing intermittently?**
A: A circuit breaker tracking the downstream's failure rate — once it crosses a threshold, fail fast without attempting the call for a cooldown period, then send a trial request to test recovery.

**Q: How do you evolve a public API without breaking existing clients?**
A: Versioning (URL path, header, or content negotiation), additive-only changes within a version, and an enforced deprecation process (headers, monitoring, direct outreach) before removing an old version.

## Behavioral / Experience

**Q: Describe an incident involving a slow or cascading downstream dependency, and how it was resolved.**
A: (Tailor to experience — strong answers mention a specific resilience pattern applied afterward: circuit breaker, propagated deadline, or load shedding, plus a measured before/after improvement.)

---

## Cheat Sheet

```
http.Server         → always set ReadTimeout/WriteTimeout/IdleTimeout
http.Client         → always set Timeout, reuse across requests
srv.Shutdown(ctx)   → graceful drain for deploys
One shared deadline → derive from r.Context(), never Background() mid-chain
Retry               → only idempotent ops, backoff + jitter, capped
Circuit breaker     → fail fast on a known-failing dependency
Load shedding       → concurrency limit + fast 503, not unbounded queuing
```

---

## Related Topics

- [Junior](junior.md) · [Middle](middle.md) · [Senior](senior.md) · [Professional](professional.md) · [Tasks](tasks.md)
