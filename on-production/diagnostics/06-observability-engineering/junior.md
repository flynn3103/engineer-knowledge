# Observability Engineering — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Observability Engineering** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Topic:** [Observability Engineering Roadmap](README.md)
> **Focus:** What observability *is*, and how it differs from monitoring. The three pillars — logs, metrics, traces — and the idea that the real unit is a wide structured event. Emitting your first correlated signal: a `trace_id` that appears in both a span and a log. Why "find the one affected customer" is the whole game.

---

## Core Concepts

### 1. Observability is about *unanticipated* questions

A monitoring dashboard answers a question you asked at design time. Observability answers a question you ask *now*, for the first time, during an incident — "show me error rate, but only for app version 4.2.1, in eu-west, for customers on the enterprise plan." If you can answer that without shipping new code, you are observable. If you have to add instrumentation and redeploy first, you are merely monitored. The whole discipline is built around preserving your ability to ask the question you haven't thought of yet.

### 2. The three signals answer different questions about the *same* event

A log says *what happened* ("charge failed: card declined"). A metric says *how much, in aggregate* ("error rate is 2%"). A trace says *what path this request took and where the time went* ("checkout → payments(900ms) → bank(870ms)"). They are not competitors; they are three views of one underlying reality. The mistake is treating them as three separate tools owned by three separate teams. The skill is **correlating** them: the metric tells you *that* something spiked and *when*; the trace tells you *which* requests; the log tells you *why* each one failed.

### 3. The real unit is the wide structured event

Charity Majors' core argument (in *Observability Engineering*) is that "logs, metrics, traces" describes the *storage formats*, not the goal. What you actually want is **one arbitrarily-wide structured event per unit of work** — per request, per job — carrying *everything you knew* at that moment: user ID, build version, region, feature flags, latency, error, downstream call durations. From that one rich event you can derive metrics (count them), reconstruct traces (group by `trace_id`), and read them like logs. Emit narrow, pre-aggregated data and you've thrown away the ability to ask new questions. Emit wide events and you keep it.

### 4. High cardinality is the superpower, not the enemy

In the [metrics](../04-metrics/) world, high-cardinality labels (like `user_id`) are *forbidden* because they explode the time-series database. In the *event* world, high cardinality is exactly what lets you find the **one affected customer** out of a million. The same data that kills a TSDB is the data that solves the 3 a.m. bug. The difference is the storage model: events are stored raw and queried, not pre-aggregated into fixed time series. (Cardinality's *cost* is real, though — see [telemetry-cost](../14-telemetry-cost-and-sampling-strategy/).)

### 5. Correlation is the thing that turns three signals into observability

A `trace_id` shared across a span and every log line for that request is the single most valuable thing a junior can add. It turns "I see an error metric spiked" into "click the spike → see the exemplar trace → read the logs for that exact request." Without correlation you have three disconnected data sources and you debug by guessing which log goes with which spike. With it, you debug by *following one thread*.

---

## Observability vs Monitoring

This is the central distinction of the whole roadmap, so it's worth making concrete.

| | **Monitoring** | **Observability** |
|---|---|---|
| **Question type** | Known-unknowns — "is the thing I worried about broken?" | Unknown-unknowns — "why is *this specific weird thing* happening?" |
| **Built from** | Dashboards + alerts you defined ahead of time | Rich events you query interactively |
| **New question costs** | Add instrumentation, deploy, wait | Type a new query |
| **Best at** | "CPU is high," "error rate exceeded 1%" | "Only enterprise users in eu-west on v4.2.1 see this" |
| **Data** | Pre-aggregated, low-cardinality | Raw, high-cardinality, high-dimensionality |
| **The failure it catches** | The one you predicted | The one you didn't |

**The defining test — the 3 a.m. question.** A customer emails: "checkout has been failing for me all morning." No dashboard shows it; the global error rate looks fine because it's *one* customer out of a million.

- A **monitored** system: you're stuck. There's no `customer_id` dashboard. You start adding logging and redeploying, hoping to catch it next time.
- An **observable** system: you query your events — `filter error=true, group by customer_id`, find the one customer, then `filter customer_id=X, group by build_version` and discover they're pinned to an old client that calls a deprecated endpoint. Five minutes, no deploy.

Observability **includes** monitoring — you still build dashboards and alerts for the failures you *can* predict (that's what the `monitoring-alerting` skill is about). The difference is that monitoring is where you *stop* when you're not observable, and where you *start* when you are.

> The control-theory root: a system is observable if you can reconstruct its internal state from its outputs. Distributed systems broke the assumption that you could just inspect the state directly (SSH in and look), so we had to reconstruct it from emitted telemetry instead.

---

## The Three Pillars and the Wide Event

### The classic framing

| Pillar | Shape | Answers | Cardinality tolerance |
|---|---|---|---|
| **Logs** | Timestamped events (ideally structured) | "What happened to this thing?" | High |
| **Metrics** | Numbers aggregated over time | "How much, in aggregate? What's the trend?" | **Low** (labels must be bounded) |
| **Traces** | A tree of spans for one request | "What path did this request take? Where was the time?" | High |
| **Profiles** *(4th)* | Sampled CPU/memory by code location | "Which function is burning the CPU / leaking memory?" | High |

These are real and useful — each sibling roadmap ([logging](../02-logging/), [metrics](../04-metrics/), [tracing](../05-tracing/), [continuous-profiling](../12-continuous-profiling/)) goes deep on one.

### Why "three pillars" is also a *critique*

The "three pillars" model is criticised (most prominently by Charity Majors) because it leads teams to build **three disconnected silos** — a logging system, a metrics system, a tracing system — each storing the *same events* in a different, lossy way, with no thread connecting them. You spot a spike in the metrics tool, then go *guess* which logs in the logging tool correspond to it.

The reframing: **the pillars are an implementation detail. The real unit is the arbitrarily-wide structured event.** Capture one wide event per request with high cardinality (many distinct values) and high dimensionality (many fields), store it raw, and *query* it. From that:

- **Metrics** = count/aggregate the events.
- **Traces** = group the events by `trace_id` and order by time.
- **Logs** = just read the events.

You stop pre-deciding what's a "metric" vs a "log" and instead keep the rich data, deriving each view on demand.

### A wide event, concretely

```json
{
  "timestamp": "2026-06-22T03:14:22.481Z",
  "trace_id": "7c1e9b3a5f2d4a8e",
  "span_id": "a1b2c3d4",
  "service": "checkout",
  "endpoint": "POST /checkout",
  "http_status": 500,
  "error": true,
  "error_kind": "payment_declined",
  "duration_ms": 902,
  "db_duration_ms": 14,
  "payment_duration_ms": 870,
  "user_id": "u_99214",
  "customer_plan": "enterprise",
  "region": "eu-west-1",
  "build_version": "4.2.1",
  "feature_flags": ["new_checkout", "fast_path"],
  "device": "ios-17.2",
  "retry_count": 2
}
```

Every one of those fields is a **dimension you can slice by**. Group by `region`, by `build_version`, by `customer_plan`, by `error_kind` — each grouping is a question you didn't have to anticipate. *That* is observability.

---

## Code Examples

The single highest-value thing a junior can do is **correlate signals with a `trace_id`**. Here's a minimal OpenTelemetry span, plus getting that span's `trace_id` into a structured log line.

### Go — a span with attributes, and trace_id in the log

```go
package main

import (
	"context"
	"log/slog"
	"net/http"
	"os"
	"time"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/trace"
)

var tracer = otel.Tracer("checkout")
var logger = slog.New(slog.NewJSONHandler(os.Stdout, nil))

func checkout(w http.ResponseWriter, r *http.Request) {
	// Start a span — this is the unit of a trace. It carries a trace_id.
	ctx, span := tracer.Start(r.Context(), "POST /checkout")
	defer span.End()

	userID := r.Header.Get("X-User-Id")
	// Attributes are the "wide event" fields — slice by any of them later.
	span.SetAttributes(
		attribute.String("user.id", userID),
		attribute.String("customer.plan", "enterprise"),
		attribute.String("region", "eu-west-1"),
		attribute.String("build.version", "4.2.1"),
	)

	start := time.Now()
	err := charge(ctx, userID)
	dur := time.Since(start)

	// THE KEY MOVE: put the trace_id in the log so log <-> trace correlate.
	sc := span.SpanContext()
	log := logger.With(
		slog.String("trace_id", sc.TraceID().String()),
		slog.String("span_id", sc.SpanID().String()),
		slog.String("user_id", userID),
		slog.Int64("duration_ms", dur.Milliseconds()),
	)

	if err != nil {
		span.RecordError(err) // attach the error to the trace
		span.SetAttributes(attribute.Bool("error", true))
		log.Error("checkout failed", slog.String("error", err.Error()))
		http.Error(w, "payment failed", 500)
		return
	}
	log.Info("checkout ok")
	w.Write([]byte("ok"))
}

func charge(ctx context.Context, _ string) error { return nil } // stub
```

Now a single request produces a **span** (with `trace_id`, attributes, error) *and* a **log line carrying the same `trace_id`**. In your backend you can jump from one to the other.

### Python — the same correlation with the OTel SDK

```python
import json, logging, time
from opentelemetry import trace

tracer = trace.get_tracer("checkout")
logger = logging.getLogger("checkout")

def checkout(user_id: str):
    # A span is the trace unit; attributes are the wide-event fields.
    with tracer.start_as_current_span("POST /checkout") as span:
        span.set_attribute("user.id", user_id)
        span.set_attribute("customer.plan", "enterprise")
        span.set_attribute("region", "eu-west-1")
        span.set_attribute("build.version", "4.2.1")

        ctx = span.get_span_context()
        trace_id = format(ctx.trace_id, "032x")   # hex, the form backends show

        start = time.monotonic()
        try:
            charge(user_id)
            ok = True
        except Exception as e:
            span.record_exception(e)
            span.set_attribute("error", True)
            ok = False

        # Structured log line carrying the SAME trace_id.
        logger.info(json.dumps({
            "trace_id": trace_id,
            "user_id": user_id,
            "duration_ms": int((time.monotonic() - start) * 1000),
            "error": not ok,
        }))

def charge(_): ...  # stub
```

### A structured "wide event" you can query

Whether you emit it as a log, a span, or both, aim for *one rich event per request* rather than ten thin ones:

```json
{
  "trace_id": "7c1e9b3a5f2d4a8e", "service": "checkout",
  "endpoint": "POST /checkout", "http_status": 500, "error": true,
  "error_kind": "payment_declined", "duration_ms": 902,
  "user_id": "u_99214", "customer_plan": "enterprise",
  "region": "eu-west-1", "build_version": "4.2.1", "device": "ios-17.2"
}
```

> Don't reach for the full OpenTelemetry Collector setup yet — that's [`middle.md`](middle.md). At this level, the win is small and real: **emit spans, and put the `trace_id` in your logs.**

---

## What Observability Costs

| What | Cost | Notes |
|---|---|---|
| Starting a span | microseconds | Cheap on the hot path; cost is in *export*, not creation. |
| Adding an attribute | negligible | More attributes = more dimensions to slice by — usually worth it. |
| Putting `trace_id` in a log | one extra field | Essentially free; the highest value-per-byte change you can make. |
| Storing wide events / traces | grows with volume × width | This is the real bill — see [telemetry-cost](../14-telemetry-cost-and-sampling-strategy/). |
| High-cardinality **metric labels** | can melt a TSDB | High cardinality is fine in *events*, dangerous in *metrics*. Know the difference. |

The headline for a junior: **emitting is cheap; storing everything forever is not.** That's why senior teams *sample* (keep a representative subset of traces) — covered at [`middle.md`](middle.md) and in depth at [telemetry-cost](../14-telemetry-cost-and-sampling-strategy/). For now, emit rich events; learning to control their cost comes next.

---

## Best Practices

1. **Put a `trace_id` in every log line.** The cheapest, highest-leverage thing you can do. It's what turns three pillars into one connected story.
2. **Emit structured events, not prose.** `{"event":"charge_failed","user_id":"u_42"}` is queryable; `"charge failed for u_42"` is not.
3. **Emit one *wide* event per request, not ten thin ones.** Attach everything you know — user, region, version, durations — to a single event.
4. **Prefer auto-instrumentation to start.** OpenTelemetry's agents/libraries instrument your HTTP server and DB client for free; add manual spans only where the auto ones aren't enough. (Detail in [`middle.md`](middle.md).)
5. **Use OpenTelemetry, not a vendor's proprietary SDK.** It's the standard; it keeps you portable across backends.
6. **Think "what question might I ask?" when choosing attributes.** Every attribute is a future slice. `build_version` and `region` are nearly always worth it.
7. **Don't fall into the silo trap.** A log, a metric, and a trace for the same event with no shared ID is three problems, not one solution. Correlate them.

---

## Edge Cases & Pitfalls

- **A trace that doesn't propagate.** If service A starts a trace but doesn't pass the context to service B, B starts a *new* trace and the journey is broken in two. **Context propagation** (passing the `trace_id` across the network) is what keeps it whole — see [`middle.md`](middle.md).
- **Logs and traces that don't share a `trace_id`.** You have both pillars but can't connect them. You'll debug by guessing which log goes with which trace. Always emit the `trace_id` in logs.
- **Treating observability as "buy a tool."** A Datadog/Honeycomb subscription doesn't make you observable; *emitting rich, correlated, queryable events* does. The tool is the backend, not the discipline.
- **Putting high-cardinality data in metric labels.** `user_id` as a Prometheus label is a classic TSDB-killer. The *same* field in an event is correct. Know which world you're in.
- **One thin event per log statement.** Ten `log.info()` calls scattered through a handler give you ten disconnected fragments; one wide event at the end gives you a queryable record.
- **Sampling away the errors.** Naïve random sampling can drop the rare failing traces you most need. (Tail-based sampling fixes this — [telemetry-cost](../14-telemetry-cost-and-sampling-strategy/).)

---

## Common Mistakes

1. **Confusing monitoring with observability.** Building more dashboards is not the same as being able to ask new questions. The test is the 3 a.m. unanticipated bug.
2. **No `trace_id` in logs.** The single most common reason teams "have all three pillars" but still debug blind.
3. **Emitting unstructured prose logs.** You can't `group by` a sentence. Structure everything.
4. **Low dimensionality.** Emitting only `status` and `latency`, then being unable to ask "which region / version / customer?" Add the dimensions *before* the incident.
5. **Treating the pillars as separate products owned by separate teams.** Silos defeat the whole point — correlation is the goal.
6. **Believing high cardinality is always bad.** It's bad for *metrics*, essential for *events*. The blanket rule "no high cardinality" throws away your superpower.
7. **Skipping OpenTelemetry for a quick vendor SDK.** Locks you in and makes correlation across signals harder later.

---

## Tricky Points

1. **"Observability" is a property of the system, not a product you install.** You can buy a great backend and still be unobservable if you emit thin, uncorrelated data. Conversely, a system emitting rich correlated events is observable even with humble tooling.
2. **A trace and a "wide event" can be the same thing.** A span *is* a structured event with timing and a `trace_id`. The mental shift is to stop seeing them as separate and start seeing one rich event that happens to have duration.
3. **The same high-cardinality field is forbidden in one storage model and required in another.** This trips up people who learned metrics first ("never use `user_id`!") and then can't understand why event-based observability *wants* it.
4. **More dimensions cost almost nothing to emit but everything if missing.** You can't slice by a field you didn't record. The asymmetry argues for emitting generously (within cost limits) — you can always ignore a field, but you can't query one you never captured.
5. **Auto-instrumentation gives breadth; manual gives depth.** Auto-instrumentation traces your framework's boundaries for free but knows nothing about *your* business logic. The valuable attributes (`customer_plan`, `cart_value`) are ones only you can add.

---

## Apply it

1. Choose one small, known input for **Observability Engineering**.
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

- What problem does Observability Engineering solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
