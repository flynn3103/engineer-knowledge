# Metrics — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Metrics** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Topic:** [Metrics Roadmap](README.md)
> **Focus:** Labels and the cardinality cliff. Naming and units that tools depend on. The Four Golden Signals, RED, and USE — *in practice*, on a real service. How to instrument an HTTP handler so it's actually debuggable, not just decorated.

---

## Core Concepts

### 1. A label multiplies your series count

The cost of a metric is **(number of label keys) → (product of each key's distinct values)**. A counter with labels `method` (5 values) × `status` (6 values) × `endpoint` (20 values) = 600 series. That's fine. Add `user_id` (1,000,000 values) and you have 600,000,000 series. The TSDB stores each one. **Every label you add multiplies, it doesn't add.** This is the single most important arithmetic in metrics.

### 2. Labels must be bounded and predictable

A good label has a **small, finite, predictable** set of values you could write on a whiteboard: HTTP method, status class, region, endpoint *template*, queue name. A bad label has an **unbounded or unpredictable** value set: user ID, request ID, email, full URL, raw error message, timestamp. The test: *"Can the number of distinct values grow without limit as the system runs?"* If yes — it's not a label, it's a log field.

### 3. The right names are the ones tools already understand

`http_request_duration_seconds`, `_total`, `_bytes` aren't arbitrary style — Prometheus's tooling, Grafana's auto-units, and alerting libraries *parse* these suffixes. A counter not ending in `_total`, or a duration in `_ms` instead of `_seconds`, works but fights the ecosystem at every turn. Conventions are an API.

### 4. Measure the well-known signals before the clever ones

Most incidents are caught by latency, traffic, error rate, and saturation. Teams discover this the hard way, after an outage where the dashboard had forty bespoke business metrics and not one of them showed the error rate climbing. Instrument RED/golden-signals *first*; add domain-specific metrics second.

### 5. Instrument at the boundary, label with the route

Time the *whole request handler* (so no code path escapes the measurement) and label with the *route template*, the *method*, and the *status class*. That single instrumented middleware gives you RED for every endpoint with bounded cardinality — the highest-leverage metric you will ever add.

---

## Labels & Cardinality

A metric without labels is one time series. The moment you add labels, you create one series per **combination** of label values:

```text
http_requests_total{method="GET",  status="200"}   ← series 1
http_requests_total{method="GET",  status="500"}   ← series 2
http_requests_total{method="POST", status="200"}   ← series 3
http_requests_total{method="POST", status="500"}   ← series 4
                    └── 2 methods × 2 statuses = 4 series ──┘
```

The total cardinality of a metric is the **product** of the distinct values of each label:

| Labels | Distinct values | Series |
|---|---|---|
| (none) | — | 1 |
| `method` | 5 | 5 |
| `method`, `status` | 5 × 6 | 30 |
| `method`, `status`, `endpoint` | 5 × 6 × 20 | 600 |
| `method`, `status`, `endpoint`, `region` | 5 × 6 × 20 × 4 | 2,400 |
| **+ `user_id`** | × 1,000,000 | **2,400,000,000** 💥 |

Everything up to `region` is healthy. Adding `user_id` turns 2,400 series into 2.4 *billion*. Each series consumes memory in the TSDB's index, RAM for the active head block, and disk forever. This is a **cardinality explosion**, and it is the defining failure mode of metrics.

### Why user-ID labels specifically kill a TSDB

A TSDB like Prometheus keeps an **inverted index** mapping every label value to the series containing it, and holds recently active series in memory. Series count — not sample count — drives RAM. A million-user label means a million index entries and a million in-memory series *per metric that carries it*. Prometheus's own guidance: keep total active series in the low millions per server; a single careless `user_id` label blows past that on day one. The symptom is your monitoring server OOM-killing itself — which means you go blind *exactly when* you need to see.

### The fix: dimension, don't identify

| You want to know… | ❌ Lethal label | ✅ Bounded label |
|---|---|---|
| Per-endpoint latency | `path="/users/42/orders/98"` | `route="/users/:id/orders/:id"` |
| Errors by customer tier | `customer_id="cus_8X2k"` | `tier="enterprise"` |
| Failures by cause | `error="connection reset by peer at 10.2..."` | `error_type="upstream_timeout"` |
| Slow region | `ip="203.0.113.7"` | `region="eu-west-1"` |

The pattern: replace the *identity* with the *category it belongs to*. You lose "which user" (go to logs/traces for that) and keep "which kind of user" (bounded, aggregatable, cheap).

> When you genuinely need per-user numbers, that's a job for **logs**, **traces with attributes**, or a purpose-built analytics store (a wide-event system like Honeycomb, or a data warehouse) — not the metrics TSDB. This boundary is the heart of the metrics-vs-logs distinction from [`junior.md`](junior.md).

---

## The Cardinality Cliff — A Failure Story

> A real-shaped incident, anonymised but representative of dozens.

A payments team adds a histogram to track checkout latency. Reasonable. Someone wants to debug a specific customer's slow checkouts, so they add a `merchant_id` label "temporarily." There are 40,000 merchants. The histogram has 12 buckets. So the series math is:

```
12 buckets  ×  40,000 merchants  ×  4 status classes  ×  3 regions
   = 5,760,000 series  for ONE histogram
```

Prometheus RAM climbs over two days from 6 GB to 28 GB. At 02:30 it OOMs, restarts, replays its WAL, OOMs again — a crash loop. **All dashboards and alerts for the entire fleet go dark**, because they share that Prometheus. The payments incident the `merchant_id` label was added to debug is now invisible, along with everything else.

**Diagnosis:** `topk(10, count by (__name__)({__name__=~".+"}))` (run on a healthy replica) showed `checkout_duration_seconds` at 5.7M series, 200× the next metric. **Fix:** drop the `merchant_id` label; replace with `merchant_tier` (4 values). Series for that metric: `12 × 4 × 4 × 3 = 576`. Per-merchant debugging moved to traces, where `merchant_id` is a perfectly fine span attribute.

**Lessons:**
1. "Temporarily add a high-cardinality label" is how almost every TSDB outage starts.
2. The blast radius of a cardinality bomb is *every* tenant of that monitoring server, not just the metric you touched.
3. Identity belongs in traces/logs; the metric carries the *category*.
4. Put a **cardinality budget** and an alert on series count *before* you need them. (Covered in [`senior.md`](senior.md) and [`professional.md`](professional.md).)

---

## Naming & Units

Names are an interface contract with every tool and human downstream. The conventions (Prometheus / OpenMetrics):

| Rule | Example | Why |
|---|---|---|
| `snake_case`, lowercase | `http_request_duration_seconds` | Consistency; some backends are case-sensitive. |
| Prefix with the subsystem | `db_query_duration_seconds` | Groups related metrics, avoids collisions. |
| **Base SI units, in the suffix** | `_seconds`, `_bytes`, `_ratio` | Grafana auto-formats; alerts assume it. Never `_ms`, `_kb`. |
| Counters end in `_total` | `http_requests_total` | Tooling identifies counters by this suffix. |
| No units *and* `_total` mixed wrong | `requests_total` ✅, `request_count_total` ❌-ish | One suffix, the right one. |
| Don't put label data in the name | `requests_total{method="GET"}` ✅, `get_requests_total` ❌ | Labels are for slicing; names are for the *what*. |
| Describe the thing, not the source | `payment_authorizations_total` | Survives refactors; readable on a dashboard. |

### Units: pick the base and never deviate

- **Time → seconds.** Always. `0.025` not `25`. The dashboard divides into ms for display; your *data* stays in seconds so every metric is comparable and aggregatable.
- **Size → bytes.** `1048576` not `1024` "KB". Same reason.
- **Ratios → unitless `0`–`1`**, suffix `_ratio`, not `_percent`. `0.95` not `95`. (Percent is a display concern.)
- **Counts of things → plain count**, counter suffix `_total`.

```text
✅  http_request_duration_seconds      (histogram)
✅  http_requests_total                (counter)
✅  process_resident_memory_bytes      (gauge)
✅  cache_hit_ratio                    (gauge, 0..1)
❌  responseTimeMs                     (camelCase, wrong unit, no type signal)
❌  request_count                      (counter without _total)
❌  memory_kb                          (non-base unit)
❌  http_get_500_requests              (label data baked into the name)
```

> Anti-pattern: encoding a label into the metric *name* (`http_get_requests_total`, `http_post_requests_total`). Now you can't sum across methods without regex gymnastics. Use one metric, a `method` label.

---

## The Four Golden Signals

From the Google SRE book — *if you measure only four things about a user-facing system, measure these:*

| Signal | What it is | Type | Example metric |
|---|---|---|---|
| **Latency** | How long requests take. **Split success vs error latency** — a fast 500 shouldn't flatter your numbers. | Histogram | `http_request_duration_seconds` |
| **Traffic** | Demand on the system. | Counter → rate | `http_requests_total` |
| **Errors** | Rate of failed requests (and the *kind*: 5xx, timeouts, wrong-but-200). | Counter | `http_requests_total{status=~"5.."}` |
| **Saturation** | How "full" the system is — the resource closest to its limit. The leading indicator of imminent failure. | Gauge | `queue_depth`, `memory_used_ratio` |

The crucial subtlety on **latency**: measure failed and successful requests *separately*. A flood of fast `500`s can make your latency histogram *look better* while the system is on fire. Track `http_request_duration_seconds{status="200"}` distinct from the error path.

The crucial subtlety on **saturation**: it's the *early warning*. Latency and errors tell you the system is *already* hurting; saturation (queue filling, memory climbing, connection pool near max) tells you it's *about to*. The on-call who watches saturation gets paged before the customer notices.

---

## RED & USE

Two complementary lenses. **RED** is for the things that *serve requests* (services, endpoints, queues). **USE** is for the things that *get consumed* (CPU, memory, disk, connection pools).

### RED — for services

| Letter | Metric | Query shape |
|---|---|---|
| **R**ate | requests per second | `rate(http_requests_total[1m])` |
| **E**rrors | failed requests per second (or error ratio) | `rate(http_requests_total{status=~"5.."}[1m])` |
| **D**uration | latency distribution | `histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))` |

RED is three metrics that give you a service's health at a glance. Apply it to *every* service and you have a uniform dashboard you can read for systems you've never seen.

### USE — for resources

| Letter | Metric | Example |
|---|---|---|
| **U**tilisation | % of time the resource was busy | CPU `node_cpu_seconds_total`, pool `db_connections_in_use / db_connections_max` |
| **S**aturation | amount of queued/waiting work | run-queue length, connection-pool wait time, GC pressure |
| **E**rrors | error events from the resource | disk I/O errors, connection failures, OOM-kills |

The trick most people miss: **utilisation and saturation are different**. A CPU can be 100% utilised and *not* saturated (everything fits). A CPU at 70% utilisation *with a growing run-queue* is saturated — work is waiting. Saturation, again, is the leading indicator.

```text
   RED  → "is this SERVICE serving requests well?"   (rate, errors, duration)
   USE  → "is this RESOURCE healthy?"                (utilisation, saturation, errors)
   Golden Signals ≈ RED + saturation, framed for user-facing systems.
```

You don't pick one; you use RED on your endpoints and USE on the CPU/memory/pools they run on. Together they cover "the service is slow" *and* "because the DB pool is saturated."

---

## Instrumenting a Service Correctly

The highest-leverage thing you can do: one middleware that produces RED for every endpoint with bounded cardinality.

**The rules:**
1. **Time the whole handler** — wrap it, so early returns and panics are still measured.
2. **Label with `method`, `route` (template!), `status` class** — bounded, gives full RED slicing.
3. **One histogram for duration, one counter for requests** — the counter's per-status split *is* your error rate; the histogram *is* your latency.
4. **Increment an in-flight gauge** for saturation.
5. **Never** put the concrete path, user ID, or request ID in a label.

This single middleware replaces a dozen ad-hoc metrics scattered through handlers, and it's correct by construction.

---

## Code Examples

### Go — RED middleware with bounded labels

```go
package metrics

import (
	"net/http"
	"strconv"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
)

var (
	requests = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "http_requests_total",
		Help: "Total HTTP requests by method, route, and status class.",
	}, []string{"method", "route", "status_class"}) // ALL bounded labels

	duration = promauto.NewHistogramVec(prometheus.HistogramOpts{
		Name:    "http_request_duration_seconds",
		Help:    "Request latency by method and route.",
		Buckets: prometheus.DefBuckets,
	}, []string{"method", "route"})

	inFlight = promauto.NewGauge(prometheus.GaugeOpts{
		Name: "http_requests_in_flight",
		Help: "Requests currently being served (saturation signal).",
	})
)

// statusRecorder captures the status code the handler writes.
type statusRecorder struct {
	http.ResponseWriter
	code int
}

func (r *statusRecorder) WriteHeader(c int) { r.code = c; r.ResponseWriter.WriteHeader(c) }

// Instrument wraps a handler for ONE route. `route` is the TEMPLATE,
// e.g. "/users/:id" — never the concrete path.
func Instrument(route string, next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		inFlight.Inc()
		defer inFlight.Dec()

		rec := &statusRecorder{ResponseWriter: w, code: 200}
		start := time.Now()
		next(rec, r) // measured even on panic if you add recover()

		statusClass := strconv.Itoa(rec.code/100) + "xx" // "2xx","4xx","5xx" — 5 values, bounded
		requests.WithLabelValues(r.Method, route, statusClass).Inc()
		duration.WithLabelValues(r.Method, route).Observe(time.Since(start).Seconds())
	}
}
```

Note `status_class` (`2xx`, `4xx`, `5xx`) rather than the raw status code — 5 values instead of 60, and it's what alerts actually query (`rate(...{status_class="5xx"})`). Note `route` is the template passed in, never `r.URL.Path`.

### Python — RED with `prometheus_client`, route as label

```python
from prometheus_client import Counter, Histogram, Gauge
import time
from functools import wraps

REQUESTS = Counter(
    "http_requests_total", "HTTP requests by method/route/status class.",
    ["method", "route", "status_class"],
)
DURATION = Histogram(
    "http_request_duration_seconds", "Request latency by method/route.",
    ["method", "route"],
)
IN_FLIGHT = Gauge("http_requests_in_flight", "Requests in flight (saturation).")

def instrument(route):                       # route is the TEMPLATE
    def deco(handler):
        @wraps(handler)
        def wrapper(request):
            IN_FLIGHT.inc()
            start = time.perf_counter()
            status = 500
            try:
                response = handler(request)
                status = response.status_code
                return response
            finally:
                IN_FLIGHT.dec()
                cls = f"{status // 100}xx"    # bounded: 2xx/4xx/5xx
                REQUESTS.labels(request.method, route, cls).inc()
                DURATION.labels(request.method, route).observe(time.perf_counter() - start)
        return wrapper
    return deco
```

The `finally` is load-bearing: `status` defaults to `500`, so an exception that escapes the handler is recorded as a `5xx`, not silently dropped.

### Java — Micrometer with bounded tags

```java
import io.micrometer.core.instrument.*;

public class RedInstrumentation {
    private final MeterRegistry registry;
    RedInstrumentation(MeterRegistry registry) { this.registry = registry; }

    public Response handle(String method, String route, Request req, Handler h) {
        Timer.Sample sample = Timer.start(registry);
        registry.gauge("http_requests_in_flight", inFlight.incrementAndGet());
        int status = 500;
        try {
            Response resp = h.apply(req);
            status = resp.status();
            return resp;
        } finally {
            inFlight.decrementAndGet();
            String cls = (status / 100) + "xx";          // bounded
            registry.counter("http_requests_total",
                "method", method, "route", route, "status_class", cls).increment();
            sample.stop(Timer.builder("http_request_duration_seconds")
                .tags("method", method, "route", route)
                .publishPercentileHistogram()             // export buckets
                .register(registry));
        }
    }
    private final java.util.concurrent.atomic.AtomicInteger inFlight =
        new java.util.concurrent.atomic.AtomicInteger();
}
```

Micrometer's gotcha: if you pass an unbounded value as a tag (e.g. `userId`), it silently creates a meter per value. Micrometer offers `MeterFilter.maximumAllowableTags(...)` to cap this — a safety net worth wiring in (see [`senior.md`](senior.md)).

### Node — `prom-client` RED middleware (Express)

```js
const client = require("prom-client");

const requests = new client.Counter({
  name: "http_requests_total",
  help: "HTTP requests by method/route/status class.",
  labelNames: ["method", "route", "status_class"],
});
const duration = new client.Histogram({
  name: "http_request_duration_seconds",
  help: "Request latency.",
  labelNames: ["method", "route"],
  buckets: [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10],
});
const inFlight = new client.Gauge({
  name: "http_requests_in_flight",
  help: "Requests in flight.",
});

function redMiddleware(req, res, next) {
  inFlight.inc();
  const end = duration.startTimer();
  res.on("finish", () => {
    // req.route.path is Express's TEMPLATE, e.g. "/users/:id" — NOT req.path
    const route = (req.route && req.route.path) || "unknown";
    const cls = `${Math.floor(res.statusCode / 100)}xx`;
    requests.labels(req.method, route, cls).inc();
    end({ method: req.method, route });
    inFlight.dec();
  });
  next();
}
module.exports = redMiddleware;
```

`req.route.path` is the Express *route template* (`/users/:id`); `req.path` is the concrete path (`/users/42`) and would be a cardinality bomb. This distinction is the whole game.

### Rust — `metrics` macros with bounded labels

```rust
use metrics::{counter, gauge, histogram};
use std::time::Instant;

// `route` MUST be a template string with a small, fixed set of values.
fn record_request(method: &str, route: &'static str, status: u16, started: Instant) {
    let class = format!("{}xx", status / 100); // 2xx/4xx/5xx
    counter!("http_requests_total",
        "method" => method.to_string(),
        "route" => route,
        "status_class" => class).increment(1);
    histogram!("http_request_duration_seconds",
        "method" => method.to_string(),
        "route" => route).record(started.elapsed().as_secs_f64());
}

fn in_flight_guard() -> impl Drop {
    gauge!("http_requests_in_flight").increment(1.0);
    scopeguard::guard((), |_| gauge!("http_requests_in_flight").decrement(1.0))
}
```

Using `&'static str` for `route` is a small but real defence — it nudges you toward compile-time-known template strings rather than runtime-built paths.

---

## Pull vs Push — First Contact

Two ways your metrics reach the monitoring system. (Trade-offs in depth: [`senior.md`](senior.md).)

| | **Pull (scrape)** | **Push** |
|---|---|---|
| Who initiates | Monitoring server fetches `/metrics` every N seconds | Your service sends metrics out |
| Examples | Prometheus | StatsD, OTLP push, Graphite |
| Good for | Long-lived services (web servers, daemons) | Short-lived jobs (cron, batch, serverless) that die before a scrape |
| "Is it up?" | Free — a failed scrape *is* a down signal | Needs a separate heartbeat |
| Service discovery | The server needs to know your targets | The service needs to know the collector |

The middle-level takeaway: **pull for anything long-running, push for anything ephemeral.** A Lambda that runs for 200ms can't wait around for a 15-second scrape — it pushes (or writes to a push-gateway / OTLP collector) and exits. A web server lives for weeks — it exposes `/metrics` and lets Prometheus pull.

---

## Coding Patterns

### Pattern 1 — Status *class*, not status *code*

```go
statusClass := strconv.Itoa(code/100) + "xx" // 2xx/3xx/4xx/5xx — 5 values
```

Five bounded values, and it's exactly what error-rate alerts match on. The exact code (`429` vs `503`) lives in logs.

### Pattern 2 — Route template, never the path

```python
DURATION.labels(method, route_template).observe(...)   # "/users/:id"
# NOT: DURATION.labels(method, request.path)           # "/users/42" → bomb
```

### Pattern 3 — Bucket the unbounded into the bounded

When you *must* slice by something unbounded, slice by its *class*: `customer_tier` not `customer_id`, `error_type` not `error_message`, `status_class` not full URL. Map identity → category at the instrumentation site.

### Pattern 4 — Default status to error in `finally`

```python
status = 500           # pessimistic default
try:
    status = handler().status_code
finally:
    record(status)     # an escaped exception is recorded as 5xx, not lost
```

### Pattern 5 — A cardinality allow-list for free-form labels

If a label value comes from user input or an external system, **map it through an allow-list** before using it as a label; anything unknown becomes `"other"`. This caps cardinality at the source.

```go
var allowed = map[string]bool{"web": true, "ios": true, "android": true}
func clientLabel(raw string) string { if allowed[raw] { return raw }; return "other" }
```

---

## Clean Code

- **Bounded labels only.** If you can't enumerate the values, it's a log field.
- **Route templates, status classes, regions, tiers** — categories, not identities.
- **Base units in the name** (`_seconds`, `_bytes`), counters `_total`. Non-negotiable; tools depend on it.
- **One middleware for RED**, declared once; don't scatter ad-hoc latency timers through handlers.
- **Map external/user-supplied values through an allow-list** before labelling.
- **Document each metric's labels** and their *expected value set* next to the declaration. The next person needs to know `status_class` is `{2xx,4xx,5xx}`, not free text.

---

## Best Practices

1. **Estimate cardinality before you add a label.** Multiply the distinct values. If the product can grow with traffic/users, stop.
2. **Adopt RED for every service and USE for every resource.** Uniformity means any engineer can read any dashboard.
3. **Split latency by success vs error.** A fast 500 must not flatter your p99.
4. **Watch saturation, not just latency/errors** — it's the leading indicator that pages you *before* customers.
5. **Use the route template, status class, region, tier** — never the path, code, IP, or ID.
6. **Put a series-count alert on your TSDB itself** (`prometheus_tsdb_head_series`) — catch the next cardinality bomb before it OOMs you. (Detail: [`senior.md`](senior.md).)
7. **Prefer one well-labelled metric over many name-encoded metrics.** `http_requests_total{method=...}`, not `http_get_requests_total`.

---

## Edge Cases & Pitfalls

- **The framework gives you the path, not the template.** Stock instrumentation that labels by `req.path` is a latent cardinality bomb. Always confirm you're getting the *route*.
- **404s on random URLs.** A scanner hitting `/aaaa`, `/bbbb`, … explodes the `route` label if you label *unmatched* requests by their path. Label all unmatched routes as `"unmatched"` / `"other"`.
- **Error message as a label.** `error="dial tcp 10.2.3.4:5432: connection refused"` — the IP and port make it unbounded. Use `error_type="connection_refused"`.
- **High-cardinality leaking through a low-cardinality label.** `version="1.2.3-abc123-dirty-2026..."` looks bounded but a per-build suffix makes it grow with deploys. Watch for sneaky unbounded values.
- **Summaries can't be re-aggregated** — if your team standardised on summaries, your fleet p99 is wrong. Migrate latency to histograms.
- **Histogram bucket bounds baked too coarse.** If all your traffic is 1–5ms but buckets jump 5ms→25ms→100ms, your p50 estimate is mush. (Bucket design: [`senior.md`](senior.md).)
- **Two services emitting the same metric name with *different* label sets.** Queries and recording rules break. Standardise label sets across services. (Fleet standards: [`professional.md`](professional.md).)

---

## Common Mistakes

1. **A `user_id` / `request_id` / `email` label.** The cardinality bomb. #1 cause of TSDB outages.
2. **Labelling by concrete path** instead of route template.
3. **Raw status code (60 values) where the class (5) would do**, and where alerts query the class anyway.
4. **Encoding labels in the metric name** (`api_v2_get_users_latency`) so you can't aggregate.
5. **Measuring only latency and errors, forgetting saturation** — paged *after* the outage instead of before.
6. **Average latency on the dashboard** because the histogram felt like more work. Averages hide the long tail.
7. **No series-count monitoring on the TSDB itself**, so the first sign of a cardinality bomb is the OOM.
8. **Different services, different names for the same thing** (`latency_ms` here, `request_seconds` there). No cross-service dashboard possible.

---

## Tricky Points

1. **Cardinality is a product, not a sum.** Three labels of 10 values each is 1,000 series, not 30. Intuition lies here; do the multiplication.
2. **A histogram already carries cardinality** — one series *per bucket* per label combination. A 12-bucket histogram with 600 label combos is 7,200 series before you've added anything. Histograms are not free.
3. **"Bounded" is about the *value set*, not the *label name*.** `region` is fine; `host` might be fine (dozens) or a bomb (autoscaling to thousands of ephemeral pods). Know your value set.
4. **`status_class` of `5xx` includes your *own* bugs and *downstream* failures.** For alerting you often want to separate "we failed" from "they failed" — consider an `error_source` label (bounded: `internal`/`upstream`/`client`).
5. **Saturation has no universal unit.** It might be queue length, pool wait time, memory ratio, or run-queue depth — whatever resource is closest to its ceiling. Pick the right one per resource; don't fake a generic "saturation" number.
6. **RED's "errors" and golden-signals' "errors" can disagree** with HTTP status. A `200 OK` carrying `{"error": "..."}` in the body is an error your status-based metric misses. Decide what *counts* as an error and instrument *that*.

---

## Apply it

1. Find a real component where **Metrics** affects an interface or dependency.
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

- Which boundary is most affected by Metrics?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
