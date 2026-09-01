# Production Debugging — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Production Debugging** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Distributed tracing follows one request across services

```go
ctx, span := tracer.Start(ctx, "handleOrder")
defer span.End()
span.SetAttributes(attribute.String("order.id", orderID))
```

A trace is a tree of **spans** — one per unit of work (an HTTP handler, a DB query, a downstream call) — linked by a shared trace ID propagated through `context.Context` and, across service boundaries, through request headers (`traceparent` in the W3C Trace Context standard). OpenTelemetry is the standard, vendor-neutral way to instrument this in Go.

### 2. Correlate logs, metrics, and traces via the same ID

The fastest incident triage happens when a single trace ID (or request ID) appears in: the trace viewer (showing the full call tree and where time went), the logs (showing what each service logged during that request), and can be cross-referenced against metrics dashboards for the same time window. Instrumenting all three with the same ID from day one is far cheaper than retrofitting it during an incident.

### 3. Reading a flame graph

```
|--------------------- handleRequest (100%) ---------------------|
|---- parseJSON (5%) ----|-------- queryDB (80%) --------|-- render (15%) --|
                          |-- Query (75%) --|
                          |-- Scan (5%) --|
```

Width represents time/samples; height represents call-stack depth. **Wide bars, regardless of depth, are where time is being spent.** A deep, narrow stack is not itself a problem — a wide one, at any depth, is what to investigate. `queryDB` dominating here means the fix effort belongs in the database call, not in JSON parsing or rendering.

### 4. Diagnosing slow queries systematically

```sql
EXPLAIN ANALYZE SELECT * FROM orders WHERE customer_id = 123 ORDER BY created_at DESC LIMIT 10;
```

A query plan showing a sequential scan where an index scan was expected almost always points to a missing or unused index (sometimes because the query doesn't match the index's column order, or a function wraps the indexed column). Pair this with the database's own slow-query log to find the actual offending queries in production, rather than guessing which ones might be slow.

### 5. High latency isn't always "slow code" — often it's queuing

```
Total latency = queue wait time + actual processing time
```

A service under load where processing time per request hasn't changed but P99 latency has spiked is usually a queuing/concurrency-limit problem, not a code-speed problem — check goroutine counts, connection pool wait times, and request-queue depth before profiling CPU.

---

## Code Examples

### Example 1 — Minimal OpenTelemetry span instrumentation

```go
func handleOrder(ctx context.Context, orderID string) error {
    ctx, span := tracer.Start(ctx, "handleOrder")
    defer span.End()

    if err := chargePayment(ctx, orderID); err != nil {
        span.RecordError(err)
        return err
    }
    return nil
}

func chargePayment(ctx context.Context, orderID string) error {
    ctx, span := tracer.Start(ctx, "chargePayment") // child span, same trace
    defer span.End()
    // ...
}
```

### Example 2 — Correlating a request ID across logs

```go
func middleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        reqID := uuid.NewString()
        ctx := context.WithValue(r.Context(), reqIDKey, reqID)
        logger := slog.With("request_id", reqID)
        logger.Info("request_start", "path", r.URL.Path)
        next.ServeHTTP(w, r.WithContext(ctx))
    })
}
```

### Example 3 — Finding a connection-pool bottleneck

```go
stats := db.Stats()
fmt.Printf("open=%d inUse=%d idle=%d waitCount=%d waitDuration=%v\n",
    stats.OpenConnections, stats.InUse, stats.Idle, stats.WaitCount, stats.WaitDuration)
```

A non-zero, growing `WaitCount`/`WaitDuration` means requests are queuing for a connection — the pool is undersized for current load, not necessarily that queries themselves got slower.

---

## Best Practices

1. Instrument distributed tracing from the start for any multi-service architecture — retrofitting during an incident is much harder.
2. Correlate logs, metrics, and traces with the same request/trace ID everywhere.
3. Read flame graphs by width, not depth, when hunting for where time is spent.
4. Check connection-pool wait metrics before assuming a latency spike is "the query got slower."
5. Run `EXPLAIN ANALYZE` against production-representative data volume, not a small dev database.

---

## Edge Cases & Pitfalls

- **A flame graph captured during a low-traffic window** may not show the code path that only becomes hot under load.
- **`EXPLAIN` (without `ANALYZE`)** shows the planner's *estimate*, not actual execution — always use `ANALYZE` for real numbers when diagnosing a live slow query (understanding it does execute the query).
- **Tracing overhead itself** can add measurable latency if sampling is set to 100% in a high-throughput service — tune the sampling rate for production.

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| Assuming a latency spike is code-speed without checking pool/queue metrics | Check `db.Stats()`/goroutine counts before profiling CPU |
| No shared trace/request ID across logs and traces | Standardize instrumentation from day one |
| Reading flame graph depth as "the problem" instead of width | Focus on wide bars regardless of stack depth |

---

## Tricky Points

- A trace showing a span taking "80% of total time" doesn't necessarily mean that code is slow — it might be waiting on a lock, a connection, or another goroutine, which requires looking at the span's own children/annotations to distinguish "computing" from "waiting."
- Sampling-based CPU profiles can under-represent very short, frequent functions relative to their real total cost — for microsecond-level functions, consider a benchmark instead of relying purely on a sampled profile.

---

## Apply it

1. Find a real component where **Production Debugging** affects an interface or dependency.
2. Write two plausible choices and the constraint that favors each one.
3. Make the smallest reversible change at that boundary.
4. Exercise the component alone, then exercise the integrated flow.
5. Keep the decision note with the evidence that selected the option.

## Verify your work

- A focused check proves the local behavior.
- An integrated check proves callers and dependencies still agree.
- Logs, traces, compiler output, or benchmarks expose the boundary.
- Reverting the change restores the previous behavior without unrelated edits.

## Review questions

- Which boundary is most affected by Production Debugging?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
