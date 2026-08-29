# Observability Engineering — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Observability Engineering** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Topic:** [Observability Engineering Roadmap](README.md)
> **Focus:** OpenTelemetry as the unifying standard — the spec, the SDKs, and the Collector. Context propagation and how a trace stays whole across services. Instrumentation strategy: auto vs manual, span design, and RED/USE/golden-signals as a default metric set. Correlating signals — exemplars (metric→trace), span→profile. The first encounter with sampling and cost.

---

## Core Concepts

### 1. OpenTelemetry won because it's the standard nobody has to lose

Before OTel there were OpenTracing, OpenCensus, and a dozen vendor agents — instrument once for Datadog, re-instrument for New Relic. OTel merged the competing standards into one **vendor-neutral** API and protocol. Now you instrument *once* with OTel and point it at *any* backend. That portability is why it won, and why "use OpenTelemetry" is the default answer to "how should we instrument?"

### 2. The API/SDK split is what makes libraries instrumentable

OTel deliberately separates the **API** (what your code and third-party libraries call to create spans) from the **SDK** (what decides sampling, batching, and where data goes). A library can depend on the *API* only and emit spans that do nothing until *your application* installs an SDK. This is why a database driver can be instrumented without forcing a backend on its users — the application chooses.

### 3. A trace is only as good as its propagation

A trace that stops at the first network call isn't a trace — it's a single-service log. **Context propagation** carries the `trace_id` and parent `span_id` across the wire (via the W3C `traceparent` header) so that service B's spans become *children* of service A's. Get this wrong and you have a pile of disconnected single-service traces; get it right and you can see one request's whole journey across forty services.

### 4. Auto-instrumentation gives breadth; manual gives the answers

Auto-instrumentation traces your HTTP server, DB client, and message queue for free — enormous breadth for zero code. But it knows *nothing* about your domain. The attributes that solve incidents — `customer.plan`, `cart.value`, `feature.flag`, `payment.provider` — only you can add. Strategy: lean on auto for coverage, add manual spans and attributes where the business logic lives.

### 5. The starting metric set is a solved problem: RED / USE / golden signals

You don't have to invent which metrics to emit. For *services*, emit **RED** (Rate, Errors, Duration). For *resources*, emit **USE** (Utilisation, Saturation, Errors). Google's **Four Golden Signals** (latency, traffic, errors, saturation) are the same idea. Emit these first, everywhere, and you'll catch the majority of incidents before reaching for anything clever.

### 6. Correlation is engineered, not accidental

For a metric spike to link to a trace, you must emit **exemplars**. For a trace span to link to a profile, the profiler must be span-aware. For logs to link to traces, the `trace_id` must be in the log. None of this happens by default — you wire it. The payoff is the single most powerful debugging move there is: spike → exemplar trace → logs for that request → profile of that span.

---

## OpenTelemetry — The Unifying Standard

OTel has three layers. Understanding which is which keeps you from confusion.

| Layer | What it is | You touch it when |
|---|---|---|
| **Specification** | The language-agnostic data model + semantics (what a span/metric/log *is*, standard attribute names) | Designing instrumentation, reading docs |
| **SDKs** (per language) | The library that implements the spec: creates spans/metrics, samples, batches, exports | Writing instrumentation code |
| **Collector** | A standalone process: receivers → processors → exporters | Designing the telemetry pipeline ([`professional.md`](professional.md)) |

### The four signals

OTel unifies all telemetry under one umbrella:

- **Traces** — spans, the per-request path. The most mature signal.
- **Metrics** — counters/gauges/histograms, with a bridge to/from Prometheus.
- **Logs** — structured records, correlated to traces via `trace_id`.
- **Profiles** — sampled CPU/memory by code location; the newest signal (cross-ref [continuous-profiling](../12-continuous-profiling/)).

The win of unifying them is **shared context**: the same `trace_id`, the same resource attributes, the same propagation, across every signal. That shared context is what makes correlation possible.

### The SDK pipeline (in-process)

```text
   your code ──► Tracer/Meter (API) ──► SDK Provider
                                          │
                                  ┌───────┴────────┐
                                  │  Sampler       │  (keep this trace?)
                                  │  SpanProcessor │  (batch)
                                  │  Exporter      │  (OTLP → Collector/backend)
                                  └────────────────┘
```

### The Collector (out-of-process)

The Collector is the hub you run *near* your services. It decouples your apps from your backends:

```text
   services ──OTLP──► [ COLLECTOR ]
                       receivers  ──► processors        ──► exporters ──► backends
                       (otlp,         (batch, tail_      (prometheus,    (Tempo, Loki,
                        prometheus)    sampling,          otlp, loki)     Honeycomb,
                                       attributes,                        Datadog)
                                       filter)
```

Why it matters even at the middle level: it means you can switch backends, add tail-based sampling, or scrub PII *without redeploying every service*. Full topology design is in [`professional.md`](professional.md).

> **Why OTel won, in one line:** instrument once, vendor-neutral, all signals share context, and the Collector lets you change everything downstream without touching app code.

---

## The Three Signals and the Wide Event, Revisited

The junior page argued the *real* unit is the wide structured event. At the middle level you see how OTel makes that practical: **a span IS a wide structured event** — it has timing, a `trace_id`, a status, and an arbitrary bag of attributes. So the modern stance is:

- Treat each **span** as the wide event for that operation. Attach every dimension you might query (`user.id`, `customer.plan`, `region`, `build.version`, `payment.provider`) as span attributes.
- Derive **metrics** from spans (span metrics / RED) or emit them directly with exemplars pointing back to spans.
- Correlate **logs** by stamping `trace_id` and `span_id` on every line.

This is the difference between "we have three pillars" and "we have one observable system." The pillars are output formats; the span-as-wide-event is the source of truth.

---

## Context Propagation

A trace spans services. For service B's work to appear as a *child* of service A's span, A must send the trace context to B, and B must read it.

```text
   Service A                                  Service B
   ┌─────────────────────┐                    ┌─────────────────────┐
   │ span: POST /checkout│                     │ span: POST /charge  │
   │ trace=7c1e span=aaaa│                     │ trace=7c1e span=bbbb│
   └──────────┬──────────┘                     │ parent=aaaa         │
              │ HTTP call                       └─────────▲───────────┘
              │ header:                                   │
              │   traceparent: 00-7c1e...-aaaa-01         │
              └───────────────────────────────────────────┘
   Same trace_id, B's span parented to A's → ONE connected trace.
```

The standard is **W3C Trace Context**: the `traceparent` header carries `version-traceid-spanid-flags`, and `tracestate` carries vendor-specific data. Key points:

- With OTel HTTP instrumentation on both ends, propagation is **automatic** — the SDK injects `traceparent` on outgoing requests and extracts it on incoming ones.
- For **non-HTTP** hops — message queues (Kafka, SQS), background jobs — you must propagate manually (inject context into the message headers, extract on the consumer). This is the #1 place traces break.
- A **propagator** is configurable; the default is W3C, but legacy systems may use B3 (Zipkin) — configure both during a migration.

When traces "split" into many single-service fragments, propagation is almost always the culprit.

---

## Instrumentation Strategy

### Auto vs manual

| | **Auto-instrumentation** | **Manual instrumentation** |
|---|---|---|
| **Effort** | Near-zero (agent or library) | Code per span/attribute |
| **Coverage** | Framework boundaries: HTTP, DB, gRPC, queues | Wherever you add it |
| **Knows your domain?** | No | **Yes** — this is its value |
| **Risk** | Noise, too many spans | Effort, inconsistency |
| **Use it for** | Baseline coverage everywhere | Business-meaningful spans & attributes |

**The strategy:** turn on auto-instrumentation *everywhere* for baseline coverage, then add **manual attributes** to the auto-created spans (you can grab the current span and `SetAttributes`) and **manual spans** only around meaningful business operations the framework can't see ("apply discount rules," "run fraud model").

### Span design — the senior-track skill, introduced

- **A span is a unit of work worth timing.** "Handle request," "query DB," "call payments." Not "increment counter."
- **Don't over-span.** A span per loop iteration is noise. A span per meaningful operation is signal.
- **Name spans by operation, low-cardinality.** `GET /users/:id`, not `GET /users/12345` — the high-cardinality detail goes in *attributes*, not the span *name*.
- **Put dimensions in attributes.** `user.id`, `customer.plan`, `region`, `build.version`. These are what you'll `group by`.
- **Record errors on the span** (`span.RecordError` + set status to error) so failures show up in the trace and in derived metrics.
- **Use semantic conventions** for standard things (`http.request.method`, `db.system`, `db.statement`) so backends and tools understand them automatically.

### What to instrument first

1. **Every service boundary** — inbound and outbound (auto gives this).
2. **Every external dependency** — DB, cache, queue, third-party API (auto gives this).
3. **The business-critical operations** — the things in your domain a PM would name (manual).
4. **RED metrics per endpoint** and **USE metrics per resource** (next section).

---

## RED, USE, and the Golden Signals

You don't invent your starting metrics. Three well-known frameworks converge:

| Framework | For | The signals |
|---|---|---|
| **RED** (Tom Wilkie) | request-driven *services* | **R**ate (req/s), **E**rrors (failed req/s), **D**uration (latency distribution) |
| **USE** (Brendan Gregg) | *resources* (CPU, disk, pool) | **U**tilisation (% busy), **S**aturation (queue/wait), **E**rrors |
| **Four Golden Signals** (Google SRE) | *services* | Latency, Traffic, Errors, Saturation |

They overlap heavily — RED ≈ golden-signals minus saturation; USE covers the resource side. **The strategy:** emit **RED for every service/endpoint** and **USE for every resource it depends on**, and you have a default observability floor that catches most incidents.

A subtlety worth internalising now: **measure success latency and error latency separately.** A flood of fast 500s (failing in 2ms) will *improve* your overall p99 while customers scream. Split duration by status class so a fast-failure can't hide.

---

## Correlating Signals

Correlation is what turns telemetry into observability. Three links, each engineered:

### 1. metric → trace, via exemplars

An **exemplar** is a `trace_id` attached to a metric data point (specifically, to a histogram bucket). When you see a latency-histogram spike, you click it and jump to an *actual slow trace* in that bucket — not "a trace from around that time," but *the* trace that produced that data point. This is the highest-leverage correlation in modern observability.

### 2. trace → log, via trace_id in logs

Covered at junior level: stamp `trace_id` and `span_id` on every log line. From a trace span you can pull every log emitted during it.

### 3. trace → profile, via span context

The newest link: a continuous profiler that is *span-aware* tags CPU samples with the active `span_id`, so you can ask "for this slow span, which function was burning CPU?" (cross-ref [continuous-profiling](../12-continuous-profiling/)).

```text
   [metric spike] ──exemplar──► [trace span] ──trace_id──► [logs]
                                      │
                                  span_id
                                      ▼
                                 [profile: hot functions for this span]
```

This chain — spike to trace to logs to profile — is the observability-driven debugging loop made concrete.

---

## Sampling — First Contact

You cannot afford to store every trace at scale (cross-ref [telemetry-cost](../14-telemetry-cost-and-sampling-strategy/)). Sampling keeps a representative subset.

| Strategy | When the decision is made | Pro | Con |
|---|---|---|---|
| **Head-based** | At trace *start* (e.g. keep 10%) | Cheap, simple, decided once and propagated | Decides *before* you know if the trace is interesting (an error you'd want is dropped) |
| **Tail-based** | At trace *end*, in the Collector | Keep *all* errors and slow traces; drop boring fast ones | Needs to buffer whole traces; more infra |

The middle-level rule: **head sampling is fine to start; move to tail-based sampling so you never drop the errors.** Naïve random head sampling at 1% means you keep one in a hundred failures — and the rare failure is exactly what you wanted. Tail sampling lets you keep 100% of errors and 1% of successes. Sampling design is its own topic — see [telemetry-cost](../14-telemetry-cost-and-sampling-strategy/).

> Sampling decisions must **propagate** with the trace context — if A samples a trace in, B must honour that, or you get half-traces.

---

## Code Examples

### Go — OTel SDK setup with OTLP export to a Collector

```go
package main

import (
	"context"
	"time"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.26.0"
)

func initTracing(ctx context.Context) (func(context.Context) error, error) {
	exp, err := otlptracegrpc.New(ctx, // export OTLP to the Collector
		otlptracegrpc.WithEndpoint("otel-collector:4317"),
		otlptracegrpc.WithInsecure())
	if err != nil {
		return nil, err
	}
	// Resource = WHO is emitting. These become attributes on every span.
	res, _ := resource.New(ctx, resource.WithAttributes(
		semconv.ServiceName("checkout"),
		semconv.ServiceVersion("4.2.1"),
		semconv.DeploymentEnvironment("prod"),
	))
	tp := sdktrace.NewTracerProvider(
		sdktrace.WithBatcher(exp),
		sdktrace.WithResource(res),
		// Head sampler: keep 10% — replace with ParentBased + tail sampling at scale.
		sdktrace.WithSampler(sdktrace.ParentBased(sdktrace.TraceIDRatioBased(0.10))),
	)
	otel.SetTracerProvider(tp)
	return tp.Shutdown, nil
}
```

### Go — auto-attributes on a span + business span

```go
import (
	"context"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/trace"
)

func handleCheckout(ctx context.Context, userID, plan string) error {
	// Enrich the auto-created HTTP server span with BUSINESS dimensions.
	span := trace.SpanFromContext(ctx)
	span.SetAttributes(
		attribute.String("user.id", userID),     // high-cardinality: fine on a span
		attribute.String("customer.plan", plan),  // a dimension you'll group by
	)

	// A manual span around domain logic auto-instrumentation can't see.
	ctx, fraud := otel.Tracer("checkout").Start(ctx, "fraud.evaluate")
	score := runFraudModel(ctx, userID)
	fraud.SetAttributes(attribute.Float64("fraud.score", score))
	fraud.End()

	return charge(ctx, userID)
}

func runFraudModel(context.Context, string) float64 { return 0.1 }
func charge(context.Context, string) error          { return nil }
```

### Python — propagation across an HTTP call (manual injection)

```python
from opentelemetry import trace
from opentelemetry.propagate import inject, extract
import requests

tracer = trace.get_tracer("checkout")

def call_payments(amount: int):
    with tracer.start_as_current_span("call.payments"):
        headers = {}
        inject(headers)          # writes 'traceparent' into headers → propagation
        return requests.post("http://payments/charge",
                             json={"amount": amount}, headers=headers)

# On the PAYMENTS service, the incoming request continues the SAME trace:
def on_request(incoming_headers):
    ctx = extract(incoming_headers)   # reads 'traceparent' → continues the trace
    with tracer.start_as_current_span("POST /charge", context=ctx):
        ...
```

### OpenTelemetry Collector — a starter config

```yaml
# otel-collector-config.yaml
receivers:
  otlp:
    protocols:
      grpc: { endpoint: 0.0.0.0:4317 }
      http: { endpoint: 0.0.0.0:4318 }

processors:
  batch: {}                          # batch before export — efficiency
  attributes:                        # scrub PII before it leaves the building
    actions:
      - { key: user.email, action: delete }
  tail_sampling:                     # keep all errors + slow traces, sample the rest
    decision_wait: 10s
    policies:
      - name: errors
        type: status_code
        status_code: { status_codes: [ERROR] }
      - name: slow
        type: latency
        latency: { threshold_ms: 500 }
      - name: sample-rest
        type: probabilistic
        probabilistic: { sampling_percentage: 5 }

exporters:
  otlp/tempo:    { endpoint: tempo:4317, tls: { insecure: true } }   # traces
  prometheus:    { endpoint: 0.0.0.0:8889 }                          # metrics
  loki:          { endpoint: http://loki:3100/loki/api/v1/push }     # logs

service:
  pipelines:
    traces:  { receivers: [otlp], processors: [attributes, tail_sampling, batch], exporters: [otlp/tempo] }
    metrics: { receivers: [otlp], processors: [batch], exporters: [prometheus] }
    logs:    { receivers: [otlp], processors: [attributes, batch], exporters: [loki] }
```

This one file shows the whole value of the Collector: PII scrubbing, tail sampling, and fan-out to three backends — none of it in your application code.

---

## Coding Patterns

### Pattern 1 — Enrich the existing span, don't create a redundant one

```go
span := trace.SpanFromContext(ctx)           // grab the auto-created span
span.SetAttributes(attribute.String("customer.plan", plan))  // add domain context
```

Auto-instrumentation already made a span for the request. Add your business attributes *to it* rather than starting a parallel one.

### Pattern 2 — Always end the span (defer / context manager / try-finally)

```python
with tracer.start_as_current_span("op") as span:   # ends automatically
    ...
```

A span that never ends never exports — and leaks. Use language constructs that guarantee `End()`.

### Pattern 3 — Status and error on the span, every error path

```go
if err != nil {
    span.RecordError(err)
    span.SetStatus(codes.Error, "charge failed")
}
```

Without this, the failing request looks fine in the trace and in any span-derived error metric.

### Pattern 4 — Resource attributes once, at startup

Set `service.name`, `service.version`, `deployment.environment` on the **Resource**, not on every span. They stamp every signal automatically and are how you slice fleet-wide.

### Pattern 5 — Propagate context into non-HTTP carriers

```python
inject(message.headers)   # producer
ctx = extract(message.headers)  # consumer
```

Queues, cron jobs, and custom RPC drop the baton unless you inject/extract explicitly.

---

## Best Practices

1. **Use OpenTelemetry. Once.** Don't scatter vendor SDKs; instrument with OTel and choose backends downstream.
2. **Auto-instrument for breadth, manually enrich for depth.** Baseline everywhere; business attributes where they matter.
3. **Set resource attributes** (`service.name`, `version`, `env`, `region`) — they make fleet-wide slicing possible.
4. **Follow semantic conventions** for standard attributes so tools light up automatically.
5. **Emit RED per service and USE per resource** as your default floor; split duration by success/error.
6. **Engineer correlation**: `trace_id` in logs, exemplars on histograms, span-aware profiles.
7. **Run a Collector** even for a small fleet — it's where sampling, PII scrubbing, and backend changes live without redeploys.
8. **Adopt tail-based sampling** so you never drop the errors you most need.
9. **Keep span names low-cardinality** (route templates) and put the high-cardinality detail in attributes.

---

## Edge Cases & Pitfalls

- **Broken propagation across queues/jobs.** Auto-HTTP propagates; async carriers don't. Inject/extract manually or your traces split.
- **High-cardinality span *names*.** `GET /users/12345` blows up the span-name dimension. Use `GET /users/:id`; the ID goes in an attribute.
- **Auto-instrumentation noise.** Some libraries create a span per redis command — thousands per request. Configure/suppress what you don't need.
- **Sampling that drops errors.** Random head sampling discards rare failures. Use tail sampling keyed on status/latency.
- **Spans that never end.** A forgotten `End()` (especially in async code) leaks and never exports — the operation just vanishes from traces.
- **Logging the `trace_id` in a different format than the backend expects.** Hex (32 chars) is standard; emit it consistently or correlation silently fails.
- **PII in attributes shipped to a third-party backend.** Emails, card numbers in spans/logs. Scrub in the Collector (`attributes` processor) before export.
- **Mismatched propagators.** One service uses B3, another W3C — traces split at the boundary. Configure a composite propagator during migration.

---

## Common Mistakes

1. **Treating OTel as just a tracing library.** It's the unifying standard for *all four signals* with shared context — that's the point.
2. **All auto, no manual.** Lots of framework spans, zero business attributes — you can trace the plumbing but not answer "which customer / plan / version."
3. **No context propagation strategy for async.** Beautiful HTTP traces that snap at the first Kafka publish.
4. **Skipping exemplars**, then wondering why you can't get from a metric spike to a trace.
5. **Over-spanning.** A span per function call buries the signal. Span meaningful operations only.
6. **Hard-coding a vendor exporter in app code** instead of exporting OTLP to a Collector — you lose the ability to change anything downstream.
7. **Random sampling that loses errors.** The rare failing trace is the one you wanted; don't let head sampling eat it.
8. **Not splitting success vs error latency**, letting fast failures flatter the p99.

---

## Tricky Points

1. **The OTel API and SDK are separate on purpose.** Code/libraries call the *API*; nothing happens until an application installs the *SDK*. This is why instrumented libraries don't force a backend on you.
2. **A sampling decision is part of the propagated context.** The `traceparent` sampled-flag tells downstream services whether the trace is being kept. If they ignore it, you get half-traces.
3. **Exemplars only work if the metric is recorded *inside* an active span** — the SDK reads the current `trace_id` at record time. Record the histogram observation where the span is current.
4. **Resource attributes are a cardinality multiplier.** Every distinct `(service, version, host, region)` combination is a separate stream — `host.name` per pod in a big fleet can be its own cardinality problem (more in [`professional.md`](professional.md)).
5. **"Logs in OTel" is the least mature signal** — many teams still ship logs via their existing stack and only stamp the `trace_id` for correlation. That's a legitimate middle-ground.
6. **Auto-instrumentation version skew** can silently change span names/attributes across a library upgrade, breaking dashboards built on them. Pin and review.

---

## Apply it

1. Find a real component where **Observability Engineering** affects an interface or dependency.
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

- Which boundary is most affected by Observability Engineering?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
