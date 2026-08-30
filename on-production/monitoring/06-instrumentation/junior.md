# Instrumentation — Junior

<!-- level-focus -->
At junior level, focus on this question:

> For one HTTP endpoint, can you add a counter and a histogram using a Prometheus client library, and explain what each metric type can and cannot tell you?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core Concept 1 — What Instrumentation Means

Instrumentation is the practice of adding code to your application that emits numbers about its own behavior — how many requests it handled, how long they took, how many items are queued right now. It is the "how" behind every dashboard and alert: before anything can be visualized or alerted on, something in the running process has to record it. This topic is specifically about *emitting metrics from code* — the client-library calls, the metric types, and where in a request's lifecycle you place them. It is not about deciding what to monitor for health, availability, or security (that's covered elsewhere), and it is not about distributed tracing or structured logs (a separate concern in this site's Observability material).

## Core Concept 2 — The Three Metric Types

A metrics client library (Prometheus's is the most common, citable example) gives you a small number of building blocks. Picking the right one is the single most important instrumentation decision at this level.

| Type | What it represents | Can go down? | Typical use |
|---|---|---|---|
| **Counter** | A cumulative total that only increases (or resets to zero on restart) | No | Requests served, errors raised, jobs processed |
| **Gauge** | A value that can go up or down, reflecting current state | Yes | Queue depth, active connections, memory used |
| **Histogram** | A distribution of observed values, bucketed | N/A (buckets only grow) | Request duration, payload size |

A common beginner mistake is picking a gauge for something that should be a counter, or vice versa. If you want to know "how many requests have we ever served," that is monotonically increasing — a counter. If you want to know "how many requests are in flight right now," that can rise and fall — a gauge. Using a gauge for a total-requests metric makes it impossible to compute a reliable rate, because a gauge doesn't tell you whether a drop was a real decrease or a process restart.

## Core Concept 3 — A Repeatable Method

For any one piece of code you want to instrument:

1. **Name the thing you're measuring** in one sentence — "how many checkout requests happen" is a counter question; "how long does a checkout request take" is a histogram question; "how many checkout jobs are queued right now" is a gauge question.
2. **Pick the metric type** from the table above based on that sentence.
3. **Name the metric** following the convention `<namespace>_<subject>_<unit>_<suffix>` — for example `http_requests_total` (counter, suffix `_total`), `http_request_duration_seconds` (histogram, unit in the name), `queue_depth` (gauge, no suffix needed since it's not cumulative).
4. **Choose labels carefully** — only dimensions with a small, bounded set of values (HTTP method, route template, status code class). Never a raw user ID, request ID, or full URL.
5. **Place the instrumentation call** at the point in code that actually observes the event — incrementing a counter when a request finishes, not when it starts, so it reflects completed work.
6. **Verify** the metric appears with a sane value by querying it locally before shipping.

## Core Concept 4 — Worked Example: Instrumenting an HTTP Handler

Using the Python Prometheus client library, instrument a simple order-lookup handler with a counter (total requests, labeled by status) and a histogram (request duration):

```python
from prometheus_client import Counter, Histogram
import time

REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "route", "status"],
)

REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "route"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5],
)

def get_order(request, order_id):
    start = time.perf_counter()
    method, route = "GET", "/orders/:id"
    try:
        order = lookup_order(order_id)
        status = "200"
        return order
    except OrderNotFound:
        status = "404"
        raise
    finally:
        REQUEST_DURATION.labels(method=method, route=route).observe(
            time.perf_counter() - start
        )
        REQUESTS.labels(method=method, route=route, status=status).inc()
```

Two things to notice: the route label is `/orders/:id` (the route *template*), never the actual path `/orders/48213` — that keeps the label's set of possible values small and bounded no matter how many distinct orders exist. And both metrics are recorded in a `finally` block, so a failed lookup still gets counted and timed, not silently dropped.

Querying this after a few minutes of traffic in PromQL:

```promql
sum(rate(http_requests_total{route="/orders/:id"}[5m])) by (status)
```

This gives requests-per-second for the route, broken down by status code — directly answering "is this endpoint being used, and how often is it failing?"

## Core Concept 5 — Cardinality: The Beginner Trap

**Cardinality** is the number of distinct label-value combinations a metric can take on. Every unique combination creates a new time series that the monitoring backend has to store and query. The single most common beginner mistake in instrumentation is putting a high-cardinality value — a user ID, an order ID, a raw request path, an email address — into a label:

```python
# Do not do this:
REQUESTS = Counter(
    "http_requests_total", "Total HTTP requests", ["user_id", "route", "status"]
)
REQUESTS.labels(user_id=current_user.id, route=route, status=status).inc()
```

If this service has 500,000 users, this one metric can generate up to 500,000 x (routes) x (status codes) time series — a **cardinality explosion**. This is a real, well-documented failure mode: it can slow down or crash the metrics backend, blow up storage and memory, and make dashboards time out, all from a single well-intentioned line of instrumentation code. The fix is always the same: labels must come from a small, closed set of known values (an enum, a fixed list of routes, a fixed list of status classes) — never from user-generated or unbounded data. If you need to investigate a single user's behavior, that's what logs or traces are for, not metric labels.

## Common Mistakes

- **Using a gauge where a counter belongs**, making rate calculations unreliable after restarts.
- **Putting unbounded values in labels** (user ID, request ID, raw path) — the cardinality-explosion trap above.
- **Naming metrics without a unit or type suffix** (`duration` instead of `duration_seconds`), making it unclear what unit a number is in.
- **Incrementing a counter before knowing the outcome**, so failures never get recorded.
- **Instrumenting duration with a gauge or a single running average** instead of a histogram, losing the ability to compute percentiles later.
- **Forgetting to register/export the metrics endpoint**, so the numbers exist in memory but are never scraped.

## Apply it

1. Pick a small function or handler in a language you know (or use the Python example above) that does one clear unit of work — an endpoint, a job handler, a function call.
2. Add a counter that increments once per completed call, labeled by outcome (`status="success"` / `status="error"`) using only closed-set label values.
3. Add a histogram that records how long each call takes, with bucket boundaries realistic for that operation (for example `1ms` to `1s` for an in-process call, `10ms` to `5s` for a network call).
4. Run the code locally to generate at least 20 calls, including at least 2 that fail, and confirm both metrics update as expected by scraping or printing the metrics endpoint.
5. Deliberately add a user-ID or request-ID label to one metric, observe how many time series it creates across a handful of calls, then remove it and explain in one sentence why it was wrong.

## Verify your work

- The counter's value equals the exact number of calls you made, split correctly by success/error label.
- The histogram shows observations distributed across more than one bucket, not all piled into one.
- You can name, for your counter and your histogram, which of the three metric types they are and why that type was the correct choice.
- You can point to the metrics endpoint output and show both metrics present with a sane current value.
- You can state, from the cardinality experiment, how many time series the unbounded label created and why that would not scale to real production traffic.

## Review questions

- What distinguishes a counter from a gauge, and what breaks if you use a gauge for a strictly-increasing quantity?
- Why does a histogram let you compute percentiles later, while a running average does not?
- Why is a route *template* the correct label value instead of the raw request path?
- What specifically happens to a metrics backend when a label takes on unbounded distinct values?
