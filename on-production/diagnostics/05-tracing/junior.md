# Tracing — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Tracing** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Topic:** [Tracing Roadmap](README.md)
> **Focus:** What a trace is. What a span is. Trace vs span vs log. Your first instrumented span in Go, Python, Java, Node, and Rust. Why a request needs context that travels *with* it.

---

## Core Concepts

### 1. A Trace Is a Tree; a Span Is a Node

The single most important sentence on this page: **a trace is a tree of spans.** The root span is the trunk. Every operation that happens *inside* it becomes a child. A child that does its own sub-work gets grandchildren. When you draw it out, you get exactly the shape of a call stack — except this call stack spans *machines*, and each node remembers how long it took.

```text
trace (id=4bf92...)
└─ span "GET /checkout"          [0ms ──────────────── 920ms]  (root)
   ├─ span "auth.verify"         [2ms ── 30ms]
   ├─ span "db.load_cart"        [31ms ──── 80ms]
   └─ span "payment.charge"      [81ms ──────────────── 915ms]  ← the slow one
      └─ span "POST stripe.com"  [90ms ──────────────── 910ms]
```

### 2. Every Span Knows Its Trace and Its Parent

A span carries three crucial IDs: its own **span ID**, the **trace ID** it belongs to, and its **parent span ID**. With these three, a backend can reassemble thousands of spans — arriving out of order, from different machines — into the exact tree above. No central coordinator is needed; the IDs *are* the structure.

### 3. Spans Measure Time

A span is started, then ended. The difference is its **duration**. This is the heart of tracing: you don't just learn that a request happened — you learn that it took 920ms, and that 834ms of that was the payment call, and that 820ms of *that* was waiting on Stripe. Each level narrows the question.

### 4. Attributes Describe; Events Annotate

You hang **attributes** on a span to describe it: which user, which URL, which database table, which status code. You add **events** to mark moments inside it: "cache miss at 40ms," "retry attempt 2 at 300ms." Attributes describe the whole span; events are timestamped points within it.

### 5. A Span Has a Status

By default a span is `Unset` (no opinion). On success you may set `Ok`. On failure you set `Error` and usually record the exception. This is what lets a trace UI paint failing spans red and lets you filter "show me only traces that errored."

### 6. OpenTelemetry Is the Lingua Franca

You don't write code against "Jaeger" or "Datadog." You write against **OpenTelemetry** — one API in your language — and *configure* where the spans go. Swap the exporter, and the same instrumented code ships to a different backend. This decoupling is why OTel won: your code outlives your vendor choice.

---

## Anatomy of a Span

Every span — in any language, on any backend — has the same skeleton. Learn it once:

| Field | Example | What it's for |
|---|---|---|
| **Trace ID** | `4bf92f3577b34da6a3ce929d0e0e4736` | Ties this span to all others in the same request. |
| **Span ID** | `00f067aa0ba902b7` | Uniquely identifies *this* span. |
| **Parent span ID** | `a1b2c3d4e5f60718` (or empty for root) | Points at the span this one happened inside. |
| **Name** | `GET /checkout`, `db.query`, `payment.charge` | A *low-cardinality* label for the kind of operation. |
| **Start time** | `2026-06-11T09:00:00.000Z` | When the span began. |
| **End time / Duration** | `+920ms` | When it ended; the difference is the duration. |
| **Attributes** | `{http.method: "GET", user.id: 42}` | Key-value descriptors of this span. |
| **Events** | `[{name: "cache.miss", time: +40ms}]` | Timestamped notes within the span. |
| **Status** | `Error` + `"deadline exceeded"` | Success/failure of the operation. |
| **Span kind** | `SERVER`, `CLIENT`, `INTERNAL`, `PRODUCER`, `CONSUMER` | The role this span plays (handling vs making a call). |

> **The name is a category, not a value.** Name a span `GET /users/:id`, never `GET /users/42`. The user ID goes in an *attribute* (`user.id=42`). If you bake the ID into the name, every request becomes a unique span name and the backend chokes. This is the cardinality rule, and it bites everyone once.

---

## Trace vs Span vs Log vs Metric

The single most clarifying table in this whole roadmap. Pin it to your memory:

| Signal | Granularity | Answers | Example |
|---|---|---|---|
| **Metric** | Aggregate | "How many / how fast, overall?" | `http_requests_total{status="500"} = 1473` |
| **Log** | One event | "What did the code say at this instant?" | `ERROR user 42 not found` |
| **Span** | One operation | "How long did *this* step take, and did it succeed?" | span `db.query` took 48ms, status Ok |
| **Trace** | One request | "What's the full path and where did the time go?" | 6 spans across 4 services, 920ms total |

The three are **complementary, not competing** — together they're called the *three pillars of observability*. A mature system emits all three and **correlates them**: the metric spike tells you something's wrong, the trace tells you *where*, and the logs (carrying the same trace ID) tell you *what exactly*. You'll learn that correlation in `middle.md`; the key idea now is that a span is *not* a fancy log — it's a measured, parented, time-bounded operation.

> A useful rule of thumb: if the thing you want to record has a **duration** and a **place in the request's path**, it's a span (or an event on a span). If it's a **count or a gauge over time**, it's a metric. If it's a **point-in-time message**, it's a log. See [`../04-metrics/README.md`](../04-metrics/README.md) and [`../02-logging/README.md`](../02-logging/README.md) for the sibling disciplines.

---

## Code Examples

All examples use **OpenTelemetry** and the same toy scenario: handle a "checkout" request, which loads a cart and charges a payment. We export to the console so you can *see* the spans without setting up a backend.

### Python

```python
# pip install opentelemetry-sdk opentelemetry-api
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter

# One-time setup: where do spans go? Here, the console.
provider = TracerProvider()
provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
trace.set_tracer_provider(provider)

tracer = trace.get_tracer("checkout")  # your first tracer

def load_cart(user_id: int) -> list[str]:
    with tracer.start_as_current_span("db.load_cart") as span:
        span.set_attribute("user.id", user_id)
        return ["book", "pen"]            # pretend DB call

def charge(user_id: int, amount: int) -> None:
    with tracer.start_as_current_span("payment.charge") as span:
        span.set_attribute("payment.amount", amount)
        span.add_event("calling payment provider")
        # pretend HTTP call to Stripe here

def checkout(user_id: int) -> None:
    # The ROOT span — everything below nests under it automatically.
    with tracer.start_as_current_span("checkout") as span:
        span.set_attribute("user.id", user_id)
        items = load_cart(user_id)
        charge(user_id, amount=len(items) * 500)

if __name__ == "__main__":
    checkout(user_id=42)
```

Run it. You'll see three JSON span objects printed. Look for `trace_id` — it's **identical** across all three. Look for `parent_id` — `db.load_cart` and `payment.charge` both point at `checkout`'s span ID. The tree is right there in the output.

### Go

```go
// go get go.opentelemetry.io/otel \
//        go.opentelemetry.io/otel/sdk/trace \
//        go.opentelemetry.io/otel/exporters/stdout/stdouttrace
package main

import (
	"context"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/exporters/stdout/stdouttrace"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
)

func main() {
	exporter, _ := stdouttrace.New(stdouttrace.WithPrettyPrint())
	tp := sdktrace.NewTracerProvider(sdktrace.WithBatcher(exporter))
	defer tp.Shutdown(context.Background()) // flush spans on exit
	otel.SetTracerProvider(tp)

	tracer := otel.Tracer("checkout")
	checkout(context.Background(), tracer, 42)
}

func checkout(ctx context.Context, tracer trace.Tracer, userID int) {
	ctx, span := tracer.Start(ctx, "checkout") // root span
	defer span.End()
	span.SetAttributes(attribute.Int("user.id", userID))

	loadCart(ctx, tracer, userID)
	charge(ctx, tracer, 1000)
}

func loadCart(ctx context.Context, tracer trace.Tracer, userID int) {
	_, span := tracer.Start(ctx, "db.load_cart") // child: ctx carries the parent
	defer span.End()
	span.SetAttributes(attribute.Int("user.id", userID))
}

func charge(ctx context.Context, tracer trace.Tracer, amount int) {
	_, span := tracer.Start(ctx, "payment.charge")
	defer span.End()
	span.AddEvent("calling payment provider")
	span.SetAttributes(attribute.Int("payment.amount", amount))
}
```

**The crucial detail in Go:** `tracer.Start(ctx, ...)` returns a *new* `ctx` that carries the span. You pass *that* `ctx` down. The child knows its parent **because the parent is hidden inside the `context.Context`.** Pass the wrong `ctx` (or `context.Background()`), and the child becomes an orphan root. This is the single most common Go tracing bug — more in `middle.md`.

### Java

```java
// build.gradle: implementation 'io.opentelemetry:opentelemetry-api'
//               implementation 'io.opentelemetry:opentelemetry-sdk'
//               implementation 'io.opentelemetry:opentelemetry-exporter-logging'
import io.opentelemetry.api.OpenTelemetry;
import io.opentelemetry.api.common.AttributeKey;
import io.opentelemetry.api.trace.Span;
import io.opentelemetry.api.trace.Tracer;
import io.opentelemetry.context.Scope;
import io.opentelemetry.exporter.logging.LoggingSpanExporter;
import io.opentelemetry.sdk.OpenTelemetrySdk;
import io.opentelemetry.sdk.trace.SdkTracerProvider;
import io.opentelemetry.sdk.trace.export.SimpleSpanProcessor;

public class Checkout {
    static final OpenTelemetry otel = OpenTelemetrySdk.builder()
        .setTracerProvider(SdkTracerProvider.builder()
            .addSpanProcessor(SimpleSpanProcessor.create(LoggingSpanExporter.create()))
            .build())
        .build();
    static final Tracer tracer = otel.getTracer("checkout");

    public static void main(String[] args) {
        Span root = tracer.spanBuilder("checkout").startSpan();
        try (Scope s = root.makeCurrent()) {          // makeCurrent => children attach
            root.setAttribute(AttributeKey.longKey("user.id"), 42L);
            loadCart(42);
            charge(1000);
        } finally {
            root.end();                                // ALWAYS end the span
        }
    }

    static void loadCart(long userId) {
        Span span = tracer.spanBuilder("db.load_cart").startSpan();
        try (Scope s = span.makeCurrent()) {
            span.setAttribute(AttributeKey.longKey("user.id"), userId);
        } finally { span.end(); }
    }

    static void charge(long amount) {
        Span span = tracer.spanBuilder("payment.charge").startSpan();
        try (Scope s = span.makeCurrent()) {
            span.addEvent("calling payment provider");
            span.setAttribute(AttributeKey.longKey("payment.amount"), amount);
        } finally { span.end(); }
    }
}
```

The `try (Scope s = span.makeCurrent())` is Java's version of "make this the current span so children attach to it," and the `finally { span.end(); }` is the non-negotiable cleanup. Forget the `end()` and the span leaks — it's never reported. (In real Java you'd usually skip all this and use the **auto-instrumentation agent**; see `middle.md`.)

### Node.js (JavaScript / TypeScript)

```js
// npm i @opentelemetry/sdk-trace-node @opentelemetry/api
const { trace } = require("@opentelemetry/api");
const { NodeTracerProvider } = require("@opentelemetry/sdk-trace-node");
const { SimpleSpanProcessor, ConsoleSpanExporter } =
  require("@opentelemetry/sdk-trace-base");

const provider = new NodeTracerProvider();
provider.addSpanProcessor(new SimpleSpanProcessor(new ConsoleSpanExporter()));
provider.register(); // installs the context manager (async_hooks under the hood)

const tracer = trace.getTracer("checkout");

function loadCart(userId) {
  return tracer.startActiveSpan("db.load_cart", (span) => {
    span.setAttribute("user.id", userId);
    span.end();
    return ["book", "pen"];
  });
}

function charge(amount) {
  return tracer.startActiveSpan("payment.charge", (span) => {
    span.addEvent("calling payment provider");
    span.setAttribute("payment.amount", amount);
    span.end();
  });
}

function checkout(userId) {
  tracer.startActiveSpan("checkout", (span) => {       // root
    span.setAttribute("user.id", userId);
    const items = loadCart(userId);                    // child, automatically
    charge(items.length * 500);
    span.end();
  });
}

checkout(42);
```

`startActiveSpan` runs your callback *with the span as the active context*, so anything you call inside becomes a child automatically. You still must call `span.end()` yourself — Node won't do it for you.

### Rust (`tracing` + OpenTelemetry)

```rust
// Cargo.toml:
//   tracing = "0.1"
//   tracing-subscriber = "0.3"
use tracing::{info, instrument};

#[instrument]                       // this attribute = "make this fn a span"
fn load_cart(user_id: u64) -> Vec<&'static str> {
    info!(user_id, "loading cart"); // an event inside the span
    vec!["book", "pen"]
}

#[instrument]
fn charge(amount: u64) {
    info!(amount, "calling payment provider");
}

#[instrument]                       // the root span: name = "checkout"
fn checkout(user_id: u64) {
    let items = load_cart(user_id); // child span, nested automatically
    charge(items.len() as u64 * 500);
}

fn main() {
    tracing_subscriber::fmt().init(); // console output of the span tree
    checkout(42);
}
```

Rust's idiomatic path is the **`tracing` crate**: the `#[instrument]` attribute turns a function into a span automatically, and `info!`/`warn!` macros emit events scoped to the current span. To ship these spans to a real backend you add `tracing-opentelemetry` (covered in `middle.md`); for now, `fmt()` prints the nested tree to your terminal.

---

## Why Request-Scoped Context Matters

Here's the question that separates "I made a span" from "I understand tracing": **how does `load_cart` know it belongs to the same request as `checkout`?**

The answer is **context propagation**, and you've already used it without naming it:

- In **Go**, the parent span lives inside the `context.Context` you passed down.
- In **Python** and **Node**, it lives in an implicit "current span" stored in a context variable (`contextvars` / `async_hooks`).
- In **Java**, `makeCurrent()` puts it in a thread-local.
- In **Rust**, the `tracing` subscriber tracks the currently-entered span.

In *all five*, the rule is identical: **a new span attaches to whatever the "current" span is.** Get the current span right, and the tree assembles itself. Lose it — start a span without the parent in scope — and you get an **orphan**: a span with no parent, floating in its own trace, disconnected from the request it actually served.

This is why "request-scoped context" is the central idea. The request carries a small invisible backpack (the active span context) as it moves through your code. Every span you start peeks in the backpack, finds its parent, and links to it. The hard part — and the subject of the entire next level — is keeping that backpack attached when the request crosses an `await`, a thread pool, a goroutine, or the network. Those boundaries *drop the backpack* unless you're careful.

> **The one-sentence takeaway:** a trace stays whole only as long as the context is propagated; the moment it's lost, the trace breaks into orphans, and a broken trace is often worse than no trace — because it *looks* like the request stopped where it actually just lost its thread.

---

## Pros & Cons of Tracing vs Logging

| Approach | Pros | Cons |
|---|---|---|
| **Tracing (spans)** | Shows the *path* and *timing* of one request across services. Built-in parent/child structure. Finds the slow hop instantly. Correlates services automatically via trace ID. | Needs context propagation (easy to break). Sampling means not every request is kept. Setup + backend required. Per-span cost if overused. |
| **Logging** | Dead simple. Works everywhere, no propagation needed. Captures arbitrary detail. See [`../02-logging/junior.md`](../02-logging/junior.md). | Flat — no built-in structure linking lines across services. You reconstruct the request manually (grep by request ID). No automatic timing. |
| **Metrics** | Tiny and cheap at any scale. Perfect for dashboards and alerts. See [`../04-metrics/README.md`](../04-metrics/README.md). | Aggregate only — can't explain *one* slow request. High-cardinality labels get expensive fast. |

The honest rule: **use all three.** A metric alert says "p99 is bad." A trace shows "it's the payment span." A log (carrying the trace ID) says "Stripe returned 429 rate-limited." Each hands off to the next.

---

## Coding Patterns

### Pattern 1 — Span Per Meaningful Boundary, Not Per Function

```python
# GOOD: spans at boundaries that matter.
with tracer.start_as_current_span("handle_request"):
    with tracer.start_as_current_span("db.query"):
        rows = db.query(...)
    with tracer.start_as_current_span("render"):
        return render(rows)

# BAD: a span for every tiny helper. Noise, cost, no insight.
with tracer.start_as_current_span("add"):  # don't trace add(a, b)
    return a + b
```

### Pattern 2 — Name by Category, Detail in Attributes

```go
// GOOD: low-cardinality name, high-cardinality detail in attributes.
ctx, span := tracer.Start(ctx, "GET /users/:id")
span.SetAttributes(attribute.Int("user.id", id))

// BAD: the ID in the name explodes cardinality.
ctx, span := tracer.Start(ctx, fmt.Sprintf("GET /users/%d", id)) // ✗
```

### Pattern 3 — Always End the Span (Prefer Scoped Helpers)

```go
ctx, span := tracer.Start(ctx, "work")
defer span.End()           // defer guarantees it ends, even on panic/early-return
```

```python
with tracer.start_as_current_span("work"):  # the `with` block ends it for you
    ...
```

### Pattern 4 — Record Errors on the Span

```python
with tracer.start_as_current_span("charge") as span:
    try:
        do_charge()
    except Exception as e:
        span.record_exception(e)
        span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
        raise
```

This is what turns a span red in the UI and makes "show me failed traces" work.

---

## Clean Code

- **End every span you start.** Use `defer` (Go), `with` (Python), `try-with-resources` (Java), `startActiveSpan` (Node). A leaked span is a span that never reports.
- **Names are categories.** `GET /orders/:id`, not `GET /orders/9931`. IDs are attributes.
- **Don't trace trivial functions.** A span has a cost and adds visual noise. Trace boundaries, not arithmetic.
- **Never put secrets or PII in attributes.** A trace backend is searchable storage; `password`, full card numbers, and tokens do not belong in spans. (Senior topic, but start the habit now.)
- **Use semantic-convention names** where they exist: `http.request.method`, `db.system`, `url.full`. Backends light up special UIs when you use the standard keys. More in `middle.md`.
- **Set status on failure.** An un-statused error span looks successful in the UI.

---

## Best Practices

1. **Write against OpenTelemetry, configure the backend separately.** Your instrumented code shouldn't mention Jaeger or Datadog by name.
2. **Start with one root span per incoming request**, then add child spans only for outbound calls and significant work.
3. **Pass context explicitly in Go** (`ctx` as the first argument, everywhere). Most Go propagation bugs are a missing or wrong `ctx`.
4. **Prefer auto-instrumentation for frameworks** (HTTP servers, DB drivers) and reserve manual spans for *your* business logic. (`middle.md` covers this split.)
5. **Look at a real trace early.** Run the console exporter, read the JSON, find the shared trace ID and the parent links. Understanding beats memorizing.
6. **Put the trace ID in your logs** so you can jump from a log line to its trace. (The correlation pattern; `middle.md`.)
7. **Resist "trace everything."** Meaningful boundaries only. Volume is cost and noise.

---

## Edge Cases & Pitfalls

- **The orphan span.** Start a span without the parent in the current context and it becomes its own root — disconnected from the request. Caused by passing `context.Background()` in Go, or losing the active context across an `await`.
- **The leaked (never-ended) span.** Forgot `span.End()` / `span.end()`. It's started but never finished, so the exporter never sends it. The trace looks truncated.
- **High-cardinality span names.** IDs, timestamps, or full URLs in the span *name* create millions of distinct names and overwhelm the backend. Keep names to a handful of categories.
- **Tracing a million-iteration loop.** One span per iteration = a span flood. Trace the loop as *one* span, or sample inside it.
- **Console exporter in production.** `SimpleSpanProcessor` + `ConsoleSpanExporter` is for learning. Production uses a *batch* processor and a real exporter (covered later) — `SimpleSpanProcessor` blocks on every span.
- **Forgetting to flush on exit.** Short-lived programs (CLIs, scripts) exit before batched spans are sent. Call `provider.shutdown()` / `tp.Shutdown(ctx)` before the program ends.
- **Clock skew between machines.** Two services with unsynchronized clocks make a child span look like it started *before* its parent. NTP matters. (Senior topic.)

---

## Common Mistakes

1. **Confusing a span with a log.** A span is a measured, parented operation with a duration. A log is a point-in-time message. Don't make a span per log line.
2. **Putting the user ID (or order ID) in the span name.** Cardinality explosion. It belongs in an attribute.
3. **Forgetting to end a span.** The most common reason "my span never shows up."
4. **Starting a child span from the wrong context** (`Background()` in Go, lost context after `await` in Python/Node). Result: orphan spans.
5. **Tracing every function.** Noise and cost. Trace boundaries.
6. **Leaving the console exporter on in production.** Slow and floods stdout.
7. **Not setting error status**, so failed operations look fine in the UI.
8. **Logging secrets into span attributes.** Traces are searchable storage; treat them like a database, not a scratchpad.
9. **Expecting a backend with no exporter configured.** No exporter = spans go nowhere. You must wire one up.
10. **Assuming the trace is complete when propagation is broken.** A truncated-looking trace usually means a *dropped context*, not a request that stopped.

---

## Tricky Points

1. **The trace ID is shared; the span ID is not.** Every span in one trace has the *same* trace ID and a *different* span ID. New juniors often expect each span to have a "new trace ID" — no.
2. **The root span has no parent ID** (it's empty/zero). That's how a backend identifies the root.
3. **A span's duration usually *contains* its children's**, but not always — async children can outlive a parent if you're not careful, which is itself a bug signal.
4. **"Current span" is implicit in most languages, explicit in Go.** Python/Node/Java/Rust track it for you in context-local storage; Go makes you thread `ctx` by hand. Both can break — Go visibly, the others invisibly.
5. **A span isn't sent the instant it ends.** Batch processors buffer and flush periodically. "I ended it but don't see it" is often just the batch interval (or a missing flush on exit).
6. **`add_event` is not the same as `set_attribute`.** Events are timestamped and can repeat; attributes describe the whole span and are singular per key.
7. **Span kind matters for the UI.** A `CLIENT` span (you calling out) and a `SERVER` span (you being called) are different roles; backends use kind to stitch cross-service edges. Default `INTERNAL` is fine for plain work.

---

## Apply it

1. Choose one small, known input for **Tracing**.
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

- What problem does Tracing solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
