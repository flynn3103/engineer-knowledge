# Metrics — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Metrics** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Topic:** [Metrics Roadmap](README.md)
> **Focus:** What a metric actually is. The four types — counter, gauge, histogram, summary. Emitting your first signals in Go, Python, Java, Node, and Rust. When a metric is the wrong tool and you wanted a log or a trace instead.

---

## Core Concepts

### 1. A metric is a number you can aggregate

The defining test of a metric is **aggregatability**: does the value still mean something when you sum, average, or max it across many sources? "Total HTTP requests" aggregates beautifully — add up every server's counter and you have the fleet total. "The user's email address" does not aggregate at all — it's an identity, not a measurement. If you cannot meaningfully combine two readings, you are looking at a log field, not a metric.

### 2. A metric is sampled, not narrated

A log is a *narration*: one line per event, with full context. A metric is a *sample*: a number read at intervals, with the context deliberately thrown away. That's the trade. You lose the ability to know *which* request was slow; you gain the ability to watch *all* requests cheaply, forever. A counter that has been incremented 4.2 billion times costs the same eight bytes to store as one that's been incremented twice.

### 3. The four types are not interchangeable

A counter that goes down is a bug. A gauge used to count total requests will give nonsense the moment the process restarts. A histogram stores buckets so percentiles can be computed *after the fact, across machines*; a summary computes percentiles *now, on this machine* and they can never be correctly merged. Picking the wrong type is the most common day-one metrics mistake, and it is silent — the dashboard shows a line, it's just the *wrong* line.

### 4. You decide what to measure at design time, and you'll guess wrong

The metric you wish you had at 3 a.m. is almost always one you didn't think mattered when you wrote the code. There is no fix for this except experience and a small set of defaults — the [Four Golden Signals](middle.md) (latency, traffic, errors, saturation). Emit those from day one and you'll be wrong far less often.

### 5. Emitting a metric is cheap; storing high-cardinality metrics is not

Incrementing a counter is a single atomic add — nanoseconds. The cost is not in *emitting*; it's in *cardinality*. A metric labelled by user ID creates one time series per user. A million users is a million time series, and that bankrupts the database. The whole of [`middle.md`](middle.md) is, in a sense, about this one trap.

---

## Metric vs Log vs Trace

These are the **three pillars of observability**. They are not competitors; they answer different questions about the same system. The single most common beginner error is reaching for the wrong one.

| | **Metric** | **Log** | **Trace** |
|---|---|---|---|
| **Answers** | "Is the system healthy *in aggregate*?" | "What happened to *this thing*?" | "What path did *this request* take across services?" |
| **Shape** | A number over time | A timestamped text/JSON event | A tree of timed spans |
| **Cost per event** | ~constant (pre-aggregated) | grows with event volume | grows with request volume |
| **Cardinality tolerance** | **Low** — labels must be bounded | High — any field is fine | High — any attribute is fine |
| **Good for** | Dashboards, alerts, trends | Forensics, audit, errors-with-context | Latency breakdown, cross-service flow |
| **Bad for** | "Which user hit the bug?" | "What's my p99 over 30 days?" | Always-on cheap health |
| **Example** | `http_requests_total{status="500"}` | `{"level":"error","user":"u_42","msg":"charge failed","err":"timeout"}` | `POST /checkout → auth(8ms) → db(120ms) → ship(40ms)` |

The decisive rule: **identity goes in logs and traces, never in metric labels.** You want to know your error *rate* (metric) and, when it spikes, *which* requests failed (logs/traces filtered by the time window the metric flagged). A user ID is perfect as a log field and lethal as a metric label.

> Sibling roadmaps: [Logging](../02-logging/README.md) and [Tracing](../05-tracing/README.md). Read all three; an engineer who only knows one of the pillars debugs with one eye closed.

---

## The Four Metric Types

| Type | Direction | What it answers | Stored as | Re-aggregatable? |
|---|---|---|---|---|
| **Counter** | up only | "How many, in total?" / "What's the rate?" | one number | ✅ yes (sum) |
| **Gauge** | up & down | "What is it *right now*?" | one number | ⚠️ sometimes (sum/avg/max — depends on meaning) |
| **Histogram** | up only (per bucket) | "What's the distribution? p50/p95/p99?" | a set of buckets + count + sum | ✅ yes (buckets add) |
| **Summary** | up only (per quantile) | "What's the p95 *on this instance*?" | pre-computed quantiles + count + sum | ❌ **no** (quantiles can't be averaged) |

### Counter

The simplest and most important. Monotonically increasing; resets to 0 only when the process restarts. The monitoring system handles the reset by detecting the drop and treating it correctly when computing rates. Use for: requests served, errors, bytes processed, tasks completed, cache hits/misses.

### Gauge

A value that can move in both directions. Use for: current memory usage, in-flight requests, queue depth, temperature, connection-pool size, a feature flag's on/off as `1`/`0`. **Do not** use a gauge for "total requests" — on restart it would reset and the monitoring system, not expecting a reset, would graph garbage.

### Histogram

The workhorse for anything where you care about the *distribution* — overwhelmingly, **latency** and **sizes**. It pre-defines a set of buckets (`≤5ms`, `≤10ms`, `≤25ms`, …) and counts how many observations fall in each. Because the buckets are just counters, they **sum cleanly across machines**, so you can compute a correct fleet-wide p99 *after the fact*. This is the killer property summaries lack. (Bucket design is subtle — see [`senior.md`](senior.md).)

### Summary

Looks like a histogram but computes the quantiles *inside the client* at observation time and exports the finished numbers (`p50=8ms`, `p99=210ms`). Cheaper to query, but the quantiles are **per-instance and cannot be merged** — you can't average ten machines' p99s into a fleet p99 (that's just mathematically wrong). Prefer histograms unless you have a specific reason. OpenTelemetry deliberately de-emphasises summaries for this reason.

```text
          observe(0.042)         observe(0.180)         observe(0.011)
                │                       │                      │
                ▼                       ▼                      ▼
   ┌───────────────────────────────────────────────────────────────┐
   │  HISTOGRAM buckets (le = "less than or equal")                │
   │  le=0.005 : 0    le=0.01 : 0    le=0.025: 1   ← 0.011 lands   │
   │  le=0.05  : 2 ← 0.042 lands     le=0.1  : 2                   │
   │  le=0.25  : 3 ← 0.180 lands     le=+Inf : 3   (total count)   │
   │  sum = 0.233                                                   │
   └───────────────────────────────────────────────────────────────┘
   Buckets are counters → they add across machines → correct global p99.
```

---

## Your First Metrics — Code Examples

The same handful of metrics in five ecosystems: a request **counter**, an in-flight **gauge**, and a request-duration **histogram**.

### Go — `prometheus/client_golang`

```go
package main

import (
	"net/http"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

var (
	requestsTotal = promauto.NewCounter(prometheus.CounterOpts{
		Name: "http_requests_total",
		Help: "Total number of HTTP requests handled.",
	})
	inFlight = promauto.NewGauge(prometheus.GaugeOpts{
		Name: "http_requests_in_flight",
		Help: "Number of requests currently being served.",
	})
	requestDuration = promauto.NewHistogram(prometheus.HistogramOpts{
		Name:    "http_request_duration_seconds",
		Help:    "HTTP request latency in seconds.",
		Buckets: prometheus.DefBuckets, // .005, .01, .025, ... 10
	})
)

func handler(w http.ResponseWriter, r *http.Request) {
	requestsTotal.Inc()      // counter: only goes up
	inFlight.Inc()           // gauge: up now...
	defer inFlight.Dec()     //        ...down when we return

	start := time.Now()
	defer func() { requestDuration.Observe(time.Since(start).Seconds()) }() // histogram

	time.Sleep(20 * time.Millisecond) // pretend to do work
	w.Write([]byte("ok"))
}

func main() {
	http.HandleFunc("/", handler)
	http.Handle("/metrics", promhttp.Handler()) // Prometheus scrapes this
	http.ListenAndServe(":8080", nil)
}
```

`curl localhost:8080/metrics` now shows your three metrics in Prometheus exposition format, including auto-generated runtime metrics (`go_goroutines`, `go_memstats_*`).

### Python — `prometheus_client`

```python
from prometheus_client import Counter, Gauge, Histogram, start_http_server
import time

REQUESTS = Counter("http_requests_total", "Total HTTP requests handled.")
IN_FLIGHT = Gauge("http_requests_in_flight", "Requests currently being served.")
LATENCY = Histogram("http_request_duration_seconds", "HTTP request latency (s).")

@LATENCY.time()            # decorator times the function into the histogram
@IN_FLIGHT.track_inprogress()   # gauge up on enter, down on exit
def handle_request():
    REQUESTS.inc()
    time.sleep(0.02)

if __name__ == "__main__":
    start_http_server(8000)     # serves /metrics on :8000
    while True:
        handle_request()
```

The decorators (`.time()`, `.track_inprogress()`) are idiomatic `prometheus_client` — they remove the manual start/stop bookkeeping.

### Java — Micrometer

```java
import io.micrometer.core.instrument.*;
import io.micrometer.prometheus.PrometheusConfig;
import io.micrometer.prometheus.PrometheusMeterRegistry;

public class Service {
    static final PrometheusMeterRegistry registry =
        new PrometheusMeterRegistry(PrometheusConfig.DEFAULT);

    static final Counter requests =
        Counter.builder("http_requests_total")
               .description("Total HTTP requests handled.").register(registry);
    static final Timer latency =        // Micrometer's histogram-backed Timer
        Timer.builder("http_request_duration_seconds")
             .description("HTTP request latency.")
             .publishPercentileHistogram()      // emit buckets, not just a summary
             .register(registry);

    static int inFlight = 0;
    static { Gauge.builder("http_requests_in_flight", () -> inFlight)
                  .register(registry); }        // gauge reads a live value

    static void handle() {
        requests.increment();
        inFlight++;
        try {
            latency.record(() -> { try { Thread.sleep(20); } catch (Exception e) {} });
        } finally { inFlight--; }
    }

    // registry.scrape() returns the Prometheus exposition text for /metrics
}
```

Micrometer is the JVM standard: one façade, many backends (Prometheus, Datadog, CloudWatch). A `Timer` is the right tool for latency — `publishPercentileHistogram()` makes it export real buckets.

### Node.js — `prom-client`

```js
const http = require("http");
const client = require("prom-client");

const requests = new client.Counter({
  name: "http_requests_total",
  help: "Total HTTP requests handled.",
});
const inFlight = new client.Gauge({
  name: "http_requests_in_flight",
  help: "Requests currently being served.",
});
const latency = new client.Histogram({
  name: "http_request_duration_seconds",
  help: "HTTP request latency in seconds.",
  buckets: [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10],
});

const server = http.createServer(async (req, res) => {
  if (req.url === "/metrics") {
    res.setHeader("Content-Type", client.register.contentType);
    return res.end(await client.register.metrics());
  }
  requests.inc();
  inFlight.inc();
  const stop = latency.startTimer();      // returns a function that records on call
  await new Promise((r) => setTimeout(r, 20));
  stop();
  inFlight.dec();
  res.end("ok");
});
server.listen(8080);
```

### Rust — `metrics` (facade) and `prometheus`

```rust
// Cargo.toml: metrics = "0.23", metrics-exporter-prometheus = "0.15"
use metrics::{counter, gauge, histogram};
use metrics_exporter_prometheus::PrometheusBuilder;
use std::time::Instant;

fn handle_request() {
    counter!("http_requests_total").increment(1);          // counter
    gauge!("http_requests_in_flight").increment(1.0);      // gauge up

    let start = Instant::now();
    std::thread::sleep(std::time::Duration::from_millis(20));
    histogram!("http_request_duration_seconds").record(start.elapsed().as_secs_f64());

    gauge!("http_requests_in_flight").decrement(1.0);      // gauge down
}

fn main() {
    // Installs a /metrics HTTP listener on :9000 by default.
    PrometheusBuilder::new().install().expect("failed to install exporter");
    loop { handle_request(); }
}
```

The `metrics` crate is a *facade* (like `log` is for logging) — your code calls `counter!`/`gauge!`/`histogram!`, and a separate exporter crate decides where they go. Clean separation, swappable backend.

---

## What a Metric Costs

| Operation | Cost | Notes |
|---|---|---|
| `counter.Inc()` | ~1 atomic add, nanoseconds | Cheap enough to put on any hot path. |
| `gauge.Set(x)` | one atomic store | Cheap. |
| `histogram.Observe(x)` | find bucket + atomic increments | Cheap; cost is in *storage*, not the call. |
| **One time series** (one label combo) | a few KB in the TSDB | This is where cost lives — multiply by cardinality. |
| **A scrape** | serialise all series to text | Grows with number of series, not request volume. |

The headline: **the call is free; the cardinality is not.** A counter with no labels is one series forever, no matter how many billions of times you increment it. The same counter labelled with `user_id` is one series *per user* — and that is how teams accidentally store millions of series and get a 2 a.m. page from their *monitoring* system. (The whole story: [`middle.md`](middle.md) → cardinality.)

---

## Coding Patterns

### Pattern 1 — Time a block with a deferred observe

```go
start := time.Now()
defer func() { requestDuration.Observe(time.Since(start).Seconds()) }()
```

`defer` (Go) / `finally` (Java) / decorator (Python) / `startTimer()` closure (Node) guarantees the observation happens *even if the function returns early or errors*. A timing that only records on the happy path under-counts your slowest requests — exactly the ones you care about.

### Pattern 2 — Gauge up/down in a matched pair

```python
IN_FLIGHT.inc()
try:
    do_work()
finally:
    IN_FLIGHT.dec()      # MUST run, or the gauge leaks upward forever
```

A gauge that gets `inc()`'d but not `dec()`'d on the error path will climb forever and lie about your load. Always pair them with `finally`/`defer`.

### Pattern 3 — Declare metrics once, globally

Define each metric **once** at package/module scope, not inside the request handler. Creating a new metric object per request is both slow and wrong (some libraries error on duplicate registration; others silently leak). Metrics are long-lived singletons.

### Pattern 4 — Use seconds and bytes as base units

```go
Name: "http_request_duration_seconds"   // ✅ seconds, not milliseconds
Name: "response_size_bytes"             // ✅ bytes, not KB
```

Conventions covered in [`middle.md`](middle.md), but start right: base SI units (seconds, bytes), `_total` suffix on counters. Dashboards and alerting rules assume it.

---

## Clean Code

- **One metric, one meaning.** Don't overload `http_requests_total` to also count background jobs. Make a second counter.
- **Name for the reader, not the writer.** `payment_authorizations_total` beats `pa_cnt`.
- **Always write a `Help` / description.** Future-you, staring at a dashboard at 3 a.m., needs to know what `widget_flux_seconds` means.
- **Base units, suffixed.** `_seconds`, `_bytes`, `_total`. Never `_ms` in a metric name even if you think in milliseconds.
- **No identity in labels.** No user IDs, emails, request IDs, full URLs as label values. (Why: [`middle.md`](middle.md).)
- **Co-locate the metric with the code it measures.** A latency histogram defined three files away from the handler it times rots.

---

## Best Practices

1. **Emit the Four Golden Signals first.** Latency, traffic, errors, saturation. They catch most incidents and cost almost nothing. (Detail in [`middle.md`](middle.md).)
2. **Pick the type by the question, not by habit.** "Total?" → counter. "Right now?" → gauge. "Distribution?" → histogram.
3. **Prefer histograms over summaries** unless you have a measured reason — histograms aggregate correctly across instances.
4. **Expose `/metrics` from day one**, even if nothing scrapes it yet. Adding it during an incident is too late.
5. **Let the client library give you runtime metrics for free** — goroutines, GC, heap, event-loop lag. Don't hand-roll them.
6. **Measure at the boundary.** Time the whole handler, count at the entry point — not deep inside helper functions where you'll miss code paths.
7. **Keep labels bounded and known in advance.** If you can't list every possible value of a label on a whiteboard, it's probably high-cardinality. Stop. ([`middle.md`](middle.md).)

---

## Edge Cases & Pitfalls

- **Counter used where a gauge belongs (or vice versa).** A "current connections" counter only goes up; a "total requests" gauge resets on restart. Both produce silently wrong graphs.
- **Histogram with default buckets on the wrong scale.** Default Prometheus buckets top out at 10 *seconds*. If you're measuring microsecond cache lookups, *every* observation lands in the first bucket and your percentiles are useless. (Bucket sizing: [`senior.md`](senior.md).)
- **Summary when you need cross-machine percentiles.** Ten instances each reporting their own p99 — there is no correct way to combine them into a fleet p99. Use a histogram.
- **Forgetting the gauge `dec()` on the error path.** The in-flight gauge leaks upward and your "load" graph lies.
- **Creating metrics inside the request handler.** Duplicate-registration errors or memory leaks, depending on the library.
- **Labelling with unbounded values.** `path="/users/12345"` creates a series per user ID baked into the URL. Use `path="/users/:id"` (the route template), not the concrete path.
- **Milliseconds in the metric name but seconds in the value** (or the reverse). The dashboard will be off by 1000× and you won't notice until an alert fires at the wrong threshold.

---

## Common Mistakes

1. **Putting identity in a metric label** (user ID, request ID, email). The #1 way juniors melt a TSDB. It belongs in a log.
2. **Using the average instead of a percentile.** The average hides your worst-served users. Use a histogram and look at p95/p99.
3. **Reading the raw counter value** (`4,210,993`) instead of its `rate()`. The raw value is meaningless; the rate is the signal.
4. **One giant catch-all metric** that tries to count everything with a dozen labels. Split it.
5. **No `Help` text / description.** Six months later nobody knows what the metric means.
6. **Measuring everything "just in case."** Every metric costs storage and cognitive load. Emit what you'll actually look at. (Anti-pattern detail: [`senior.md`](senior.md).)
7. **Confusing a histogram with a summary** and being surprised the percentiles "don't add up" across machines (summaries don't, histograms do).
8. **Re-creating a metric object per call** instead of declaring it once at module scope.

---

## Tricky Points

1. **Counters reset to zero on restart — and that's fine.** The monitoring system detects the drop and computes `rate()` correctly across the reset. Never "fix" this by making a counter that survives restarts; you'd break the rate maths.
2. **A gauge is *not* always aggregatable.** Summing "queue depth" across machines is meaningful; summing "CPU temperature" is not — you'd want the max or average. The library can't know which; *you* decide via the dashboard query.
3. **`Observe()` records into a histogram; it does not "set" anything.** Each call adds one data point to the distribution. There's no single "current value" of a histogram.
4. **`_total` is a *convention*, not magic** — but Prometheus tooling and alerting rules genuinely rely on it to identify counters. Follow it.
5. **The histogram's `_count` is itself a counter** of total observations, and `_sum` is a counter of the total of all observed values. `rate(_sum) / rate(_count)` gives you the *average* — which is exactly why you rarely want it.
6. **A metric with no observations yet may not appear at all** in the scrape output (lazy libraries) — so "the metric is missing" can mean "zero events," not "broken instrumentation." Check both.

---

## Apply it

1. Choose one small, known input for **Metrics**.
2. Predict the output or observable behavior.
3. Run the smallest example or probe that exercises the concept.
4. Change one input to trigger a failure or boundary case.
5. Explain the evidence using the guide's vocabulary.

## Verify your work

- Record the exact input, command or code path, and output.
- Repeat the probe and confirm the result is consistent.
- Show one expected success and one expected failure.
- Resolve any difference between the prediction and the evidence.

## Review questions

- What problem does Metrics solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
