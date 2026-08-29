# Tracing — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Tracing** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Topic:** [Tracing Roadmap](README.md)
> **Focus:** How a trace stays whole. In-process and cross-service context propagation (W3C `traceparent`). Manual vs auto instrumentation. Attributes, events, span links, status, span kind — done right. Putting the trace ID into your logs.

---

## Core Concepts

### 1. The Context Is the Trace; Spans Are Just Its Footprints

Reframe the whole thing: the unit that travels is **context**, not spans. A span is what gets *created* when work happens inside a context. Keep the context flowing correctly and the spans nest correctly for free. Lose the context and no amount of careful span code saves you. Propagation is the discipline of *never losing the context*.

### 2. In-Process and Cross-Service Are the Same Idea, Different Carrier

Crossing a function call inside one process and crossing the network to another process are the *same operation*: take the current context, hand it to the next unit of work. The only difference is the **carrier**. In-process the carrier is a language construct (`ctx`, `contextvars`, thread-local). Cross-service the carrier is **headers** — and you must explicitly *inject* on the way out and *extract* on the way in.

### 3. Inject on the Client, Extract on the Server

The cross-service contract has exactly two halves. The **client** span injects `traceparent` into the outgoing request headers. The **server** on the other end extracts `traceparent` from the incoming headers and starts its root span as a *child* of what it found. Get both halves and the two services share one trace. Skip either half and you get two disconnected traces that should have been one.

### 4. Auto-Instrumentation Does the Boring 80%; You Write the Meaningful 20%

You almost never hand-write spans for HTTP servers, HTTP clients, gRPC, or database drivers — instrumentation *libraries* (or a Java agent) do that, and they also handle inject/extract for you. Your job is the spans that the machine *can't* guess: the business operations (`reserve_inventory`, `score_fraud`, `apply_promotion`). The art is layering thin manual spans on top of rich auto spans.

### 5. A Span Without Good Attributes Is Half a Span

A span named `db.query` that lasted 400ms tells you *where*; the attributes (`db.system=postgresql`, `db.statement=SELECT...`, `db.rows=10000`) tell you *why*. Useful tracing is mostly about attaching the right, standard, low-cardinality-where-it-counts attributes — and never the wrong ones (PII, secrets, unbounded cardinality).

### 6. The Trace ID in Your Logs Is the Cheapest Win You'll Ever Ship

Once the trace ID is on every log line, you get bidirectional pivoting: from a slow trace, jump to its logs; from an error log, jump to its trace. This single integration turns three separate tools into one investigation. It costs a few lines in your log formatter.

---

## In-Process Context Propagation

Inside one process, the context is implicit in most languages and explicit in Go. **Every boundary that doesn't carry it forward is a place the trace can break.**

| Language | How the active context is carried | Where it silently breaks |
|---|---|---|
| **Go** | Explicit `context.Context`, threaded as the first argument. | Passing `context.Background()`; launching a goroutine with the wrong (or no) `ctx`. |
| **Python** | `contextvars` (the SDK uses them automatically). | `asyncio` is fine; **`ThreadPoolExecutor` / raw threads** lose it unless you copy the context. |
| **Node.js** | `AsyncLocalStorage` via `async_hooks` (installed by `provider.register()`). | Some callback-style libs and certain `setImmediate`/event-emitter paths break the async chain. |
| **Java** | Thread-local (`Context.current()` / `makeCurrent()`). | **New threads, executors, `CompletableFuture`** — must wrap with `Context.taskWrapping(...)`. |
| **Rust** | The `tracing` subscriber tracks the entered span. | `tokio::spawn` of a future without `.instrument(span)` loses the span. |

The pattern to internalize: **synchronous, same-thread code propagates for free; the moment you hop a thread, a pool, a goroutine, an executor, or a future, you must carry the context across by hand.** (Async runtimes and queues get a full treatment in `senior.md` and `professional.md`.)

```python
# Python: the classic in-process break — a thread pool loses the context.
from concurrent.futures import ThreadPoolExecutor
from opentelemetry import context as otel_context

def submit_with_context(pool, fn, *args):
    ctx = otel_context.get_current()          # capture HERE, on the parent thread
    def run():
        token = otel_context.attach(ctx)      # re-attach on the worker thread
        try:
            return fn(*args)
        finally:
            otel_context.detach(token)
    return pool.submit(run)
```

```go
// Go: the classic break — a goroutine that drops ctx.
go func() {
    // BAD: started a span from context.Background() -> orphan
    _, span := tracer.Start(context.Background(), "async.work")
    span.End()
}()

go func(ctx context.Context) {
    // GOOD: capture the parent ctx and pass it in
    _, span := tracer.Start(ctx, "async.work")
    span.End()
}(ctx)
```

---

## Cross-Service Propagation — W3C Trace Context

This is the heart of *distributed* tracing. When service A calls service B over HTTP, the trace context rides along in two standard headers.

### The `traceparent` header

```text
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
             │  │                                │                │
             │  └ trace-id (16 bytes hex)        └ parent span-id └ trace-flags
             └ version                              (8 bytes hex)    (01 = sampled)
```

- **version** — `00` today.
- **trace-id** — the shared ID for the whole request. Service B reuses it.
- **parent-id** — the span ID of A's *client* span. B's *server* span becomes its child.
- **trace-flags** — bit `01` means "this trace is sampled." B should honor this (parent-based sampling — see `senior.md`).

The companion **`tracestate`** header carries vendor-specific key-value state (`tracestate: rojo=00f067,congo=t61rcWk`). You rarely touch it by hand; propagators manage it.

### Inject (client) → Extract (server)

```text
   SERVICE A                                   SERVICE B
   ┌────────────────────────┐                  ┌──────────────────────────┐
   │ client span (CLIENT)   │                  │                          │
   │   inject() ──────────▶ traceparent header ──▶ extract()              │
   │                        │   over the wire  │   start server span      │
   │                        │                  │   (SERVER) as CHILD      │
   └────────────────────────┘                  └──────────────────────────┘
   Same trace_id end to end. A's client span_id = B's server parent_id.
```

If you use auto-instrumented HTTP clients and servers, **this happens for you** — the instrumentation injects on the way out and extracts on the way in. You only do it by hand for protocols the libraries don't cover (custom RPC, a message queue, a webhook).

### Configuring the propagator

OpenTelemetry defaults to W3C `traceparent`+`baggage`. If you interoperate with an older Zipkin/B3 fleet, configure a composite propagator so you read *and* write both:

```python
# Python: support W3C and B3 simultaneously (migration / mixed fleet).
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.composite import CompositePropagator
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.propagators.b3 import B3MultiFormat

set_global_textmap(CompositePropagator([
    TraceContextTextMapPropagator(),  # W3C traceparent
    B3MultiFormat(),                  # X-B3-* headers
]))
```

> **The #1 cross-service bug:** A injects W3C `traceparent`, but B only knows how to extract B3 (or vice versa). Both look correctly instrumented in isolation; together they produce *two* traces. When a trace "stops at a service boundary," check that both sides agree on the propagation format **first**.

---

## Manual vs Auto Instrumentation

| | Auto-instrumentation | Manual instrumentation |
|---|---|---|
| **What it traces** | Frameworks: HTTP server/client, gRPC, DB drivers, Kafka, Redis, AWS SDK. | *Your* business logic: `reserve_inventory`, `score_fraud`. |
| **Who writes the spans** | An agent or instrumentation library. | You. |
| **Propagation** | Handled for you (inject/extract on framework calls). | You ensure the right context is in scope. |
| **Effort** | One-time setup; near-zero per-endpoint. | Per-operation code. |
| **Coverage** | Wide but shallow — knows the call happened, not *why*. | Narrow but deep — knows the business meaning. |
| **Risk** | Span explosion; over-broad attribute capture (can grab PII from headers/queries). | Forgetting to end spans; wrong context. |

**The right answer is both.** Turn on auto-instrumentation to get the skeleton (every HTTP and DB call traced + propagated for free), then *manually* add the handful of spans that describe what your service actually does. Auto gives you the bones; manual gives you the meaning.

### Java — auto-instrumentation via the agent (zero code)

```bash
# Download opentelemetry-javaagent.jar once, then:
java -javaagent:opentelemetry-javaagent.jar \
     -Dotel.service.name=checkout \
     -Dotel.exporter.otlp.endpoint=http://collector:4317 \
     -jar checkout.jar
# Every Servlet, JDBC call, JDBC pool, Kafka client, gRPC stub is now traced
# AND traceparent is injected/extracted automatically. You wrote no span code.
```

### Python — auto-instrumentation via the launcher

```bash
pip install opentelemetry-distro opentelemetry-instrumentation-flask \
            opentelemetry-instrumentation-requests
opentelemetry-bootstrap -a install          # pull instrumentations for your libs
OTEL_SERVICE_NAME=checkout \
OTEL_EXPORTER_OTLP_ENDPOINT=http://collector:4317 \
opentelemetry-instrument python app.py      # wraps Flask, requests, psycopg2, ...
```

### Node — auto-instrumentation via a preloaded module

```js
// tracing.js — load this BEFORE your app via: node --require ./tracing.js app.js
const { NodeSDK } = require("@opentelemetry/sdk-node");
const { getNodeAutoInstrumentations } =
  require("@opentelemetry/auto-instrumentations-node");
const { OTLPTraceExporter } = require("@opentelemetry/exporter-trace-otlp-http");

new NodeSDK({
  serviceName: "checkout",
  traceExporter: new OTLPTraceExporter({ url: "http://collector:4318/v1/traces" }),
  instrumentations: [getNodeAutoInstrumentations()], // http, express, pg, redis, ...
}).start();
```

---

## Attributes, Events, Status, Kind

The four levers that turn a bare span into a useful one.

### Attributes — describe the whole span

```python
span.set_attribute("http.request.method", "POST")
span.set_attribute("http.route", "/checkout")       # template, NOT /checkout/42
span.set_attribute("db.system", "postgresql")
span.set_attribute("payment.amount_cents", 1000)    # your own namespaced key
```

Rules: prefer **semantic-convention keys** where they exist; keep values **low-to-moderate cardinality**; **never** put secrets/PII. A high-cardinality attribute (a UUID per request) is fine *as an attribute* (it doesn't multiply storage like a high-cardinality *metric label* would), but it does inflate index size — be intentional.

### Events — timestamped notes within the span

```go
span.AddEvent("cache.miss")
span.AddEvent("retry", trace.WithAttributes(attribute.Int("attempt", 2)))
```

Use events for *moments*: a cache miss, a retry, a validation failure that didn't abort. An event is closer to a structured log line scoped to this span than to an attribute.

### Status — success or failure

```java
try {
    doWork();
    span.setStatus(StatusCode.OK);                  // optional on success
} catch (Exception e) {
    span.recordException(e);                         // attaches stack as an event
    span.setStatus(StatusCode.ERROR, e.getMessage()); // paints it red, filterable
    throw e;
}
```

`recordException` + `setStatus(ERROR)` is the pair that makes "show me failed traces" work. An un-statused error is invisible to error filters.

### Span kind — the role

| Kind | Meaning | Example |
|---|---|---|
| `SERVER` | You are *handling* an inbound request. | Your HTTP handler's root span. |
| `CLIENT` | You are *making* an outbound call. | Your DB query, your HTTP call to Stripe. |
| `PRODUCER` | You *enqueue* a message. | Publishing to Kafka/SQS. |
| `CONSUMER` | You *process* a message. | A Kafka consumer handling a record. |
| `INTERNAL` | Plain in-process work. | A business-logic span. The default. |

Kind drives the UI's cross-service stitching (a `CLIENT` span links to the matching `SERVER` span). For producer/consumer across a queue, you usually link rather than parent — see `senior.md`.

---

## Semantic Conventions

OpenTelemetry publishes **semantic conventions** — standardized attribute names so that *every* backend understands `http.request.method`, `db.system`, `messaging.system`, `url.full`, regardless of who emitted them. Using them is the difference between a generic span and one that lights up a purpose-built UI (a DB span that shows the query, an HTTP span that shows the route and status).

| Domain | Key conventions (current names) |
|---|---|
| HTTP server | `http.request.method`, `http.route`, `http.response.status_code`, `url.path`, `server.address` |
| HTTP client | `http.request.method`, `url.full`, `http.response.status_code`, `server.address` |
| Database | `db.system`, `db.namespace`, `db.query.text`, `db.operation.name` |
| Messaging | `messaging.system`, `messaging.destination.name`, `messaging.operation` |
| RPC | `rpc.system`, `rpc.service`, `rpc.method` |
| General | `service.name`, `service.version` (resource), `error.type` |

Two notes: (1) the conventions **evolved** — older code uses `http.method`/`http.status_code`, newer uses `http.request.method`/`http.response.status_code`; pin a version and migrate deliberately. (2) `service.name` lives on the **Resource** (set once per process), not on each span. A missing `service.name` shows up as `unknown_service` in every backend — set it.

---

## Correlating Trace IDs Into Logs

The single highest-leverage integration in observability. Get the **trace ID** (and span ID) onto every log line, and your logs and traces become two views of the same investigation.

The mechanism: the SDK exposes the *current* span context; your log formatter reads it and adds `trace_id` / `span_id` fields.

```python
# Python: structlog/logging processor that injects trace_id into every record.
import logging
from opentelemetry import trace

class TraceContextFilter(logging.Filter):
    def filter(self, record):
        ctx = trace.get_current_span().get_span_context()
        record.trace_id = format(ctx.trace_id, "032x") if ctx.is_valid else "-"
        record.span_id = format(ctx.span_id, "016x") if ctx.is_valid else "-"
        return True
# Then add %(trace_id)s to your formatter. Every log line now carries the trace.
```

```go
// Go: pull the trace_id out of ctx for slog.
func logWith(ctx context.Context) *slog.Logger {
    sc := trace.SpanContextFromContext(ctx)
    return slog.Default().With(
        "trace_id", sc.TraceID().String(),
        "span_id", sc.SpanID().String(),
    )
}
// usage: logWith(ctx).Info("charge failed", "err", err)
```

Now the workflow is: metric alert → click the exemplar → open the trace → spot the red span → click through to *exactly the log lines* of that request (filtered by `trace_id`). Three tools, one thread. (The reverse — from a customer's error log to its trace — works identically.) See [`../02-logging/middle.md`](../02-logging/middle.md) for the structured-logging foundation this builds on. The *metric* side of the same idea (exemplars) is a `professional.md` topic.

---

## Code Examples

A complete two-service example: a `gateway` calls a `pricing` service over HTTP. The trace must span both.

### Go — manual inject/extract (what auto-instrumentation does for you)

```go
// --- gateway (client side) ---
func callPricing(ctx context.Context, tracer trace.Tracer) (*http.Response, error) {
	ctx, span := tracer.Start(ctx, "GET pricing", trace.WithSpanKind(trace.SpanKindClient))
	defer span.End()

	req, _ := http.NewRequestWithContext(ctx, "GET", "http://pricing/quote", nil)
	// INJECT the current context into the outgoing headers:
	otel.GetTextMapPropagator().Inject(ctx, propagation.HeaderCarrier(req.Header))
	return http.DefaultClient.Do(req)
}

// --- pricing (server side) ---
func pricingHandler(w http.ResponseWriter, r *http.Request) {
	// EXTRACT the context from incoming headers, then start a SERVER span as child:
	ctx := otel.GetTextMapPropagator().Extract(r.Context(),
		propagation.HeaderCarrier(r.Header))
	ctx, span := otel.Tracer("pricing").Start(ctx, "GET /quote",
		trace.WithSpanKind(trace.SpanKindServer))
	defer span.End()

	span.SetAttributes(semconv.HTTPRouteKey.String("/quote"))
	w.Write([]byte(`{"price": 100}`))
}
```

In practice you'd use `otelhttp.NewHandler` and `otelhttp.NewTransport` and never write inject/extract by hand — but seeing it once makes the magic legible.

### Python — Flask + requests, auto-instrumented

```python
# Run with: opentelemetry-instrument python gateway.py
import requests
from flask import Flask
from opentelemetry import trace

app = Flask(__name__)
tracer = trace.get_tracer("gateway")

@app.get("/checkout")
def checkout():
    # Flask auto-instrumentation already extracted the incoming context and
    # made a SERVER span. We add a manual business span underneath it:
    with tracer.start_as_current_span("business.checkout") as span:
        span.set_attribute("checkout.step", "price")
        # requests auto-instrumentation INJECTS traceparent automatically:
        resp = requests.get("http://pricing/quote")   # CLIENT span + propagation, free
        span.set_attribute("pricing.status", resp.status_code)
        return {"ok": True}
```

The two auto-instrumentations (Flask + requests) handle extract-on-entry and inject-on-exit; your one manual span carries the business meaning.

### Node — Express + axios, with the trace ID in logs

```js
// Loaded via: node --require ./tracing.js server.js  (see auto-instrument section)
const express = require("express");
const axios = require("axios");
const { trace, context } = require("@opentelemetry/api");
const app = express();

function log(level, msg, extra = {}) {
  const span = trace.getSpan(context.active());
  const sc = span?.spanContext();
  console.log(JSON.stringify({
    level, msg, ...extra,
    trace_id: sc?.traceId ?? "-",      // ← correlation: trace_id on every log line
    span_id: sc?.spanId ?? "-",
  }));
}

app.get("/checkout", async (req, res) => {
  log("info", "checkout.start");                 // carries the trace_id
  // axios auto-instrumentation injects traceparent into this outgoing call:
  const { data } = await axios.get("http://pricing/quote");
  log("info", "checkout.priced", { price: data.price });
  res.json({ ok: true });
});
```

### Java — manual span layered on the agent's auto spans

```java
// Running under -javaagent:opentelemetry-javaagent.jar: the Servlet + the
// outbound HttpClient are already traced and propagated. You add meaning:
import io.opentelemetry.api.GlobalOpenTelemetry;
import io.opentelemetry.api.trace.*;
import io.opentelemetry.context.Scope;

Tracer tracer = GlobalOpenTelemetry.getTracer("checkout");

void handleCheckout(long userId) {
    Span span = tracer.spanBuilder("business.checkout")
        .setSpanKind(SpanKind.INTERNAL).startSpan();
    try (Scope s = span.makeCurrent()) {
        span.setAttribute("user.id", userId);
        priceCart();              // the agent traces the outbound HTTP call inside
        span.setStatus(StatusCode.OK);
    } catch (Exception e) {
        span.recordException(e);
        span.setStatus(StatusCode.ERROR);
        throw e;
    } finally {
        span.end();
    }
}
```

### Rust — propagate across an HTTP call with `tracing-opentelemetry`

```rust
// Cargo.toml: tracing, tracing-opentelemetry, opentelemetry, opentelemetry-http, reqwest
use opentelemetry::global;
use opentelemetry_http::HeaderInjector;
use tracing::Instrument;
use tracing_opentelemetry::OpenTelemetrySpanExt;

async fn call_pricing() -> reqwest::Result<String> {
    let span = tracing::info_span!("GET pricing");
    async {
        let cx = tracing::Span::current().context();   // OTel context of this span
        let mut req = reqwest::Request::new(
            reqwest::Method::GET, "http://pricing/quote".parse().unwrap());
        // INJECT traceparent into the outgoing headers:
        global::get_text_map_propagator(|prop| {
            prop.inject_context(&cx, &mut HeaderInjector(req.headers_mut()));
        });
        reqwest::Client::new().execute(req).await?.text().await
    }
    .instrument(span)         // ← keep the span attached across the await
    .await
}
```

Note the `.instrument(span)` — in Rust async you must explicitly attach the span to the future, or the context is lost across the `await`. That's the Rust version of the propagation rule.

---

## Coding Patterns

### Pattern: Thread `ctx` everywhere in Go

```go
// ctx is ALWAYS the first parameter. This is the propagation contract.
func (s *Service) Checkout(ctx context.Context, userID int) error {
    ctx, span := s.tracer.Start(ctx, "Checkout")
    defer span.End()
    if err := s.loadCart(ctx, userID); err != nil { // pass ctx down
        return err
    }
    return s.charge(ctx, userID)                      // pass ctx down
}
```

### Pattern: One manual span per business operation, auto for the rest

```python
@app.post("/order")
def create_order():                       # SERVER span: auto (Flask)
    with tracer.start_as_current_span("reserve_inventory"):  # manual: business
        reserve()                          # the DB call inside: auto (psycopg2)
    with tracer.start_as_current_span("charge_payment"):     # manual: business
        requests.post(...)                 # the HTTP call inside: auto (requests)
```

### Pattern: Always pair recordException with setStatus(ERROR)

```go
if err != nil {
    span.RecordException(err)
    span.SetStatus(codes.Error, err.Error())
    return err
}
```

### Pattern: Set `service.name` on the Resource, once

```python
from opentelemetry.sdk.resources import Resource
provider = TracerProvider(resource=Resource.create({"service.name": "checkout"}))
# Without this, every backend shows "unknown_service". Non-negotiable.
```

---

## Clean Code

- **`service.name` is mandatory.** A trace without it is unattributable. Set it on the Resource.
- **Inject and extract are symmetric** — if one service injects W3C, every service must extract W3C (or run a composite propagator). Standardize fleet-wide.
- **Prefer instrumentation libraries** (`otelhttp`, `opentelemetry-instrumentation-*`, the Java agent) over hand-rolled inject/extract. Less code, fewer bugs.
- **Use semantic-convention attribute names**; namespace your custom ones (`company.checkout.step`).
- **Trace ID in every log line** — make it a shared logging-library default, not a per-service afterthought.
- **End spans with scope-bound helpers** (`defer`, `with`, try-with-resources, `startActiveSpan`) so an early return or exception can't leak them.
- **Don't let auto-instrumentation capture full request/response bodies or all headers** — that's where PII leaks in. Configure the capture list.

---

## Best Practices

1. **Turn on auto-instrumentation first**, confirm propagation works end-to-end (one trace across two services), *then* add manual business spans.
2. **Standardize one propagation format** across the fleet (W3C `traceparent`); add B3 only for interop, via a composite propagator.
3. **Put the trace ID in logs in a shared library** so every service does it identically.
4. **Set the Resource** (`service.name`, `service.version`, deployment environment) once per process.
5. **Use the right span kind** — `CLIENT`/`SERVER` for calls, `PRODUCER`/`CONSUMER` for queues — so cross-service stitching works.
6. **Record exceptions and set ERROR status** on every failure path you care about.
7. **Audit auto-instrumentation's attribute capture** for PII before shipping (headers, query strings, bodies).
8. **Test propagation explicitly**: a test that asserts service B's span has service A's trace ID. Propagation breaks silently otherwise.

---

## Edge Cases & Pitfalls

- **Format mismatch across services.** A injects W3C, B extracts only B3 → two traces. The most common "trace stops at the boundary" cause.
- **Thread-pool / executor handoff.** Python `ThreadPoolExecutor`, Java `ExecutorService`, `CompletableFuture` lose the context unless you capture-and-reattach (or wrap the executor).
- **`tokio::spawn` without `.instrument`** drops the Rust span across the spawn boundary.
- **Manual inject without a started client span.** Injecting the *parent's* context (not a fresh client span) makes the downstream a child of the wrong span — subtle but wrong nesting.
- **Auto-instrumentation capturing secrets.** Default header/query capture can grab `Authorization`, `?token=...`. Configure the denylist.
- **Mixing global and explicit propagators.** If `set_global_textmap` and a local propagator disagree, inject/extract use different formats. Pick one source of truth.
- **`http.route` set to the concrete path** (`/users/42`) instead of the template (`/users/:id`) — re-introduces the cardinality problem at the attribute level for routing UIs.
- **Logs and traces using different ID encodings** (one hex, one decimal) — they won't join. Standardize on 32-hex-char trace IDs.

---

## Common Mistakes

1. **Assuming auto-instrumentation handles your custom RPC or queue.** It covers known libraries; custom transports need manual inject/extract.
2. **Different propagation formats on the two ends of a call.** Two traces where one was intended.
3. **Forgetting to set `service.name`.** Everything shows as `unknown_service`.
4. **Losing context across a thread/goroutine/future** and not noticing because the in-process spans still *mostly* connect.
5. **Putting concrete IDs in `http.route`** or span names — cardinality returns through the back door.
6. **Recording an exception but not setting ERROR status** (or vice versa) — half-marked failures.
7. **Letting auto-instrumentation log full bodies/headers** — PII and secret leakage.
8. **Trace ID in logs done per-service, inconsistently** — some hex, some decimal, some missing. Centralize it.
9. **Injecting context without first starting a CLIENT span** — wrong parent for the downstream.
10. **Treating events like attributes** (or vice versa) — events are timestamped moments; attributes describe the whole span.

---

## Tricky Points

- **`traceparent`'s `parent-id` is the *caller's span ID*, not the trace's root.** The downstream's server span parents to the *immediate* caller's client span, building the tree hop by hop.
- **The sampled flag in `traceparent` (`-01`) is a hint the downstream should honor.** Parent-based sampling means if the parent was sampled, the child should be too — otherwise you get half-traces. See `senior.md`.
- **`baggage` ≠ span attributes.** Baggage propagates across services (in the `baggage` header) and is readable everywhere downstream; attributes stay on their span. Baggage is powerful and dangerous (it's also a PII-leak and a header-bloat vector — `professional.md`).
- **Auto + manual can double-count.** If you manually wrap an HTTP call that auto-instrumentation also wraps, you get two spans for one call. Know what's already instrumented.
- **Context extraction must happen *before* you start the server span**, or the server span won't be a child of the caller. Order matters.
- **`makeCurrent()`/`attach` must be paired with close/`detach`.** Leaking the scope corrupts the context for unrelated later work on the same thread.
- **A `CLIENT` span's duration includes network + remote processing**, while the remote `SERVER` span only covers remote processing. The gap between them is the network/queue time — a useful signal, not a bug.

---

## Apply it

1. Find a real component where **Tracing** affects an interface or dependency.
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

- Which boundary is most affected by Tracing?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
