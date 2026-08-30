# Logs, Metrics, Traces — Junior

<!-- level-focus -->
At junior level, focus on this question:

> When a single checkout request fails, which of the three signals — a log line, a metric, or a trace — do you check first, and what does each one actually tell you that the others can't?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core concepts: three signals, three different questions

Observability rests on three kinds of telemetry. They are not competing tools — they answer genuinely different questions about the same underlying event, and a system that can't inspect itself directly needs all three to be debuggable.

- **Logs** — a discrete, timestamped record of one thing that happened: `payment declined for order 8842, reason=insufficient_funds`. A log is the richest signal per event, but it only tells you about the event it was written for.
- **Metrics** — a number tracked over time, usually pre-aggregated: `checkout_errors_total`, `checkout_latency_seconds`. A metric is cheap to store forever and great for trends, but it has already thrown away the detail of any single request.
- **Traces** — the path one request took through a system, broken into timed **spans**: `api-gateway → checkout-service → payments-service → bank-sandbox`, each with a duration. A trace shows you causality and where time went, for one request, across service boundaries.

The habit to build now: a metric tells you **that** something is wrong and roughly **when**; a trace tells you **where** in the call chain it went wrong; a log tells you **why**, in detail, for one specific instance. None of the three can answer all three questions alone.

| Signal | Cardinality it tolerates | Typical storage cost | How you query it | Best question it answers |
|---|---|---|---|---|
| Logs | High (any field, any value) | Grows linearly with event volume; expensive to retain in full at scale | Full-text or field search for one request or a narrow filter | "What exactly happened, in detail, for this one thing?" |
| Metrics | Low — labels must stay bounded (a handful of known values each) | Flat and cheap regardless of traffic volume, because it's pre-aggregated | Aggregate functions over time: rate, sum, percentile | "How much, how often, and is it trending up or down?" |
| Traces | High (trace/span IDs are unique per request) | Expensive to keep for every request at volume; usually sampled | Look up by `trace_id`, view the span tree for one request | "What path did this request take, and where did the time go?" |

---

## A worked example: one failed checkout

**Scenario.** An online store has `api-gateway` → `checkout-service` → `payments-service` → an external `bank-sandbox`. A customer emails support: "my payment failed with a server error." You have a metrics dashboard, a tracing backend, and a log search tool, all keyed by `trace_id`.

**Step-by-step method:**

1. **Start with the metric** to confirm scope and timing. The checkout error-rate panel shows:

   ```
   checkout_errors_total{status="500"} rate: 0.1% (09:00–14:00) → 4.2% (14:02 onward)
   ```

   This tells you something real changed at 14:02 UTC and it's affecting roughly 1 in 24 checkouts — not just this one customer. It does **not** tell you which requests, or why.

2. **Find one representative trace** filtered by `http.status_code=500` and a timestamp near 14:02. The trace backend returns a span tree:

   ```
   trace_id=7c1e9b3a5f2d4a8e
   ├─ api-gateway            12ms
   └─ checkout-service       905ms
      └─ payments-service    891ms   ← almost all the time is here
         └─ bank-sandbox     874ms   status=ERROR
   ```

   The trace tells you **where**: the failure and the time are both in the `bank-sandbox` call, not in your own checkout logic. It does not tell you *why* the bank call failed.

3. **Pull the structured log** for that exact `trace_id` from `payments-service`:

   ```json
   {"timestamp":"2026-06-22T14:02:11.481Z","level":"error","trace_id":"7c1e9b3a5f2d4a8e",
    "service":"payments-service","event":"card_declined","reason":"insufficient_funds",
    "order_id":"8842","user_id":"u_99214"}
   ```

   The log tells you **why**, in full detail, for this exact instance: the bank declined the card for insufficient funds. Combined with the metric and the trace, you now know: it's affecting ~4% of checkouts since 14:02, the slow/failing hop is the bank call, and the specific failure reason is a real business outcome (a spike in declined cards), not a bug in your code.

Three signals, three angles, one incident understood in minutes — instead of grepping every service's logs hoping to stumble on the right lines.

---

## Emitting each signal (minimal snippets)

**A metric emission** (Go, using a Prometheus-style counter):

```go
var checkoutErrors = prometheus.NewCounterVec(
    prometheus.CounterOpts{Name: "checkout_errors_total"},
    []string{"status"}, // low-cardinality label — a handful of known values
)

func handleCheckout(w http.ResponseWriter, r *http.Request) {
    if err := charge(r.Context()); err != nil {
        checkoutErrors.WithLabelValues("500").Inc()
        http.Error(w, "payment failed", 500)
        return
    }
}
```

**A structured log line** (JSON, one event, machine-parseable):

```json
{"timestamp":"2026-06-22T14:02:11.481Z","level":"error","trace_id":"7c1e9b3a5f2d4a8e",
 "event":"card_declined","reason":"insufficient_funds","order_id":"8842"}
```

**A trace span** (Go, OpenTelemetry):

```go
ctx, span := tracer.Start(r.Context(), "payments-service.charge")
defer span.End()

span.SetAttributes(attribute.String("order.id", orderID))
if err != nil {
    span.RecordError(err)
    span.SetAttributes(attribute.Bool("error", true))
}
```

Notice the `trace_id` appears in both the trace and the log line. That shared identifier is what let you jump from the metric spike to the exact trace to the exact log in the worked example above — without it, you'd have three disconnected data sources and no way to prove they describe the same request.

---

## Common mistakes

1. **Treating logs as sufficient for everything.** Grepping across every service's logs during an incident, hoping to spot the right lines, is slow and doesn't tell you scope or trend — that's what the metric is for.
2. **Writing unstructured log lines.** `"Payment failed for user 12345"` cannot be filtered, grouped, or queried by field. `{"event":"payment_failed","user_id":"12345"}` can.
3. **Skipping the `trace_id` in log lines.** Without a shared identifier, you cannot connect a metric spike to a trace to a log line — you're left guessing which log belongs to which failure.
4. **Reading a metric as if it describes one customer.** A 4% error rate does not tell you *which* 4% — the customer emailing support might not even be in that 4%. You need the trace and log to confirm.
5. **Assuming a trace is just "logging, but distributed."** A trace's value is the *causal, timed structure* across services — the fact that 891 of 905ms happened inside one specific downstream call. A pile of unordered log lines from three services doesn't give you that structure.

---

## Apply it

1. Instrument a small two-endpoint service (e.g., `POST /checkout` calling a `charge()` function that fails 1 in 20 times) with a counter metric `checkout_errors_total`, a structured JSON log line per request including a `trace_id` field, and one span per request using any tracing library you have available.
2. Run 50 requests through it and confirm the error counter increments only on failures.
3. Pick one failed request's `trace_id` from a log line, then find the matching span for that same `trace_id` in your tracing output.
4. Delete the `trace_id` field from the log line, re-run, and try to match a failed request's log to its trace using only timestamps — note how much longer and less certain it is.
5. Write one sentence for each signal explaining specifically what it told you that the other two didn't.

## Verify your work

- The error counter's final value equals the number of failed requests you triggered, not the total request count.
- You can take one specific `trace_id` and find its log line and its span independently, and confirm they describe the same request (same order/user identifier, same approximate timestamp).
- With the `trace_id` removed, matching a log to its trace by timestamp alone produces at least one wrong or ambiguous match when requests overlap.
- You can state, for the failed request you inspected, one fact only the metric revealed, one fact only the trace revealed, and one fact only the log revealed.

## Review questions

- What does a metric tell you about an incident that a single log line cannot?
- Why does a trace need a shared `trace_id` to be useful alongside logs?
- What happens to your ability to correlate signals when a log line omits the `trace_id`?
- If you could keep only one of the three signals for this service, which would you keep, and what class of question would you lose the ability to answer?
