# Observability Engineering — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Observability Engineering** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Topic:** [Observability Engineering Roadmap](README.md)
> **Focus:** Designing observability *for a service or system under constraints*. The control-theory framing of observable vs monitorable. The three-pillars critique resolved into the arbitrarily-wide structured event, and why the cardinality that kills a TSDB is exactly what you want in a wide event. Span and data-model design that decides whether you can answer the questions you didn't anticipate. Correlating signals deeply (exemplars, span→profile). The observability-driven debugging loop, SLIs/SLOs as the user-facing layer, trace-based vs metric-based alerting, sampling's relationship to fidelity, and debugging in production.

---

## Core Concepts

### 1. Observability is a property of the *data*, not the dashboards

A system is observable if the questions can be answered from the outputs — full stop. Dashboards are a *cache* of the questions you already thought of. The senior shift is to stop optimising for "what does the dashboard show" and start optimising for "can the raw telemetry answer an arbitrary new `group by`." If the answer requires a code change and a deploy, the system was not observable for that question.

### 2. The three pillars are output formats; the wide event is the source of truth

Logs, metrics, and traces are three ways of *looking at* the same underlying thing: a record of what happened during a unit of work. Designing three separate, uncorrelated pipelines is the anti-pattern. Design **one wide event per operation** (a span, in OTel terms) and *derive* the other views from it.

### 3. Cardinality is the cost in a TSDB and the value in a wide event

The single most important conceptual unlock at this level: the exact property that makes a TSDB fall over — a field with millions of distinct values — is the property that makes a wide event powerful. In a TSDB, each label combination is a separate time series; `user.id` as a label means millions of series and an OOM. In a wide-event store, `user.id` is just another column you can filter on, and being able to slice to *one* user is the whole point. **Same data, opposite economics, because of where the aggregation happens.**

### 4. Instrumentation decisions are bets about future questions

You cannot query a dimension you didn't capture. So the design question is: *which dimensions will future-you wish were on the event?* Capture identity (user, tenant, account), provenance (build version, region, host, feature flags), and the business shape of the request (plan, cart value, payment provider). These are cheap to add at write time and impossible to reconstruct after the fact.

### 5. SLOs are the bridge from observability to the user

Raw observability lets you debug. **SLOs** turn it into a contract: a measured indicator (SLI) of user-perceived success, a target (SLO), and the budget for failure. They are the layer that decides *whether to page*, *whether to ship*, and *what "good enough" means* — and they are computed from the same telemetry that powers debugging.

### 6. Sampling trades fidelity for cost — design the trade, don't accept the default

At scale you cannot keep every event. The senior skill is choosing *what* fidelity to give up: keep 100% of errors and slow traces, sample the boring fast majority, and never let the sampler eat the rare failure you'll need. Sampling is a fidelity-allocation decision, covered in depth in [telemetry-cost](../14-telemetry-cost-and-sampling-strategy/README.md).

---

## Observability vs Monitoring — The Control-Theory Framing

The terms get used loosely; the precise distinction is worth getting exactly right, because it drives every design decision below.

**Monitoring** is the practice of watching a *predefined* set of signals against *predefined* thresholds. You enumerate the ways the system can fail, build a dashboard and an alert for each, and get paged when one trips. Monitoring answers **known-unknowns**: "Is CPU high? Is the error rate above 1%? Is the queue backing up?" You knew to ask these in advance.

**Observability** is the property of being able to ask **arbitrary new questions** of the system from the outside, *without deploying new code* — the **unknown-unknowns**. "Why are checkouts failing, but only for enterprise customers, on the new payment provider, in eu-west, since the 14:02 deploy?" Nobody built that dashboard. You answer it by slicing telemetry along dimensions you captured but never pre-aggregated.

The word is borrowed precisely from **control theory** (Rudolf Kálmán, 1960): a dynamical system is *observable* if its complete internal state can be determined in finite time from its external outputs. The analogy is exact. Your service's "internal state" is everything that happened during a request; the "outputs" are your telemetry; the system is observable if the telemetry is rich enough to reconstruct what happened — including for failure modes you never modelled.

| | **Monitoring** | **Observability** |
|---|---|---|
| Question class | Known-unknowns | Unknown-unknowns |
| Built from | Predefined dashboards & alerts | Wide events, queried ad hoc |
| New question costs | A code change + deploy | A new query |
| Data shape | Pre-aggregated metrics | High-cardinality, high-dimensionality events |
| Control-theory analogue | Watching a few known outputs | State reconstructible from outputs |
| Failure it handles | The outage you anticipated | The outage you didn't |

**Crucial nuance:** observability *subsumes* monitoring; it does not replace it. You still want a handful of cheap, pre-aggregated SLO and resource alerts — you do not want to run an ad-hoc query to discover the disk is full. The design goal is: monitor the predictable, keep the underlying events rich enough to investigate the unpredictable.

---

## The Three-Pillars Critique and the Wide Event

The "three pillars of observability — logs, metrics, traces" framing (Cindy Sridharan popularised it; Charity Majors sharpened the critique) is useful for beginners and misleading for designers. The critique:

1. **The pillars are output formats, not a goal.** Having logs *and* metrics *and* traces does not make you observable. You can have all three and still be unable to answer the 3 a.m. question — because they're three disconnected silos with no shared identity.
2. **Each pillar throws away exactly what the others need.** Metrics pre-aggregate, discarding per-request detail. Traditional logs are unstructured strings, hard to query by dimension. Traces have structure but are often sampled blind. The information you need is scattered and lossy.
3. **The real unit is the arbitrarily-wide structured event.** One event per unit of work (per request, per operation, per span), carrying *every* dimension you might want to query — dozens to hundreds of fields — stored raw and **queried, not pre-aggregated**.

A wide event for one checkout request might carry: `trace_id`, `duration_ms`, `http.status`, `http.route`, `user.id`, `tenant.id`, `customer.plan`, `cart.value`, `cart.item_count`, `payment.provider`, `payment.latency_ms`, `fraud.score`, `region`, `availability_zone`, `host.name`, `build.version`, `feature.new_checkout`, `db.pool.wait_ms`, `cache.hit`, `retry.count`, … forty fields, all on one event.

With that event, the three pillars become **projections**, computed on demand:

- A **metric** is `COUNT`/`heatmap` of these events grouped by some low-cardinality field.
- A **trace** is the set of these events sharing a `trace_id`, ordered by time and parent.
- A **log line** is one event (or a span event) rendered as text.

> **The reframing in one sentence:** don't emit three uncorrelated signals and hope to stitch them; emit one rich event and *derive* the signals — keeping the raw event so you can ask questions you didn't pre-decide.

In OTel terms, **a span IS a wide structured event**: it has timing, a `trace_id`, a status, and an arbitrary attribute bag. So the practical advice is concrete — make your spans *wide* (dense in attributes), make them *cover the meaningful operations*, and make sure the backend stores them in a way you can `group by` arbitrary attributes.

---

## Cardinality: The Killer and the Superpower

This is the section to internalise, because it explains the entire architectural split between metrics backends and observability backends.

**Cardinality** = the number of distinct values a field takes. **Dimensionality** = the number of fields. Wide events are *high* in both.

### Why cardinality kills a TSDB

A time-series database (Prometheus is the canonical example) stores one separate time series per **unique label-set**. If you have a metric `http_requests_total` with labels `{method, route, status}`, the number of series is roughly the product of the cardinalities of those labels. Add `user_id` as a label and the series count explodes to *one series per user* — millions of series, each with its own retention, index entry, and memory footprint. This is the infamous **cardinality explosion**, and it is the number-one way to take down a metrics stack. The TSDB's whole performance model assumes labels are *low*-cardinality.

```text
TSDB cost ≈ (cardinality of label A) × (B) × (C) × ...   →  one series per combination
   {method:4} × {route:50} × {status:5}        = 1,000 series        ✅ fine
   {method:4} × {route:50} × {status:5} × {user_id:2,000,000}        = 2 billion series  💥 OOM
```

So in a metrics world, `user.id` as a label is a **firing offence**. The right move there is to *not* put high-cardinality fields on metrics.

### Why the same cardinality is the superpower in a wide event

A wide-event / column store does **not** pre-aggregate. Each event is a row; each attribute is a column. `user.id` is just another column you can filter and `group by` at query time. There is no per-combination series to maintain — the cost scales with the number of *events*, not with the *cardinality of fields*. So putting `user.id`, `trace_id`, `request.id`, `cart.value` on the event is not only allowed, it is the entire reason the model exists: **you can slice to the one affected customer.**

```text
Wide-event store cost ≈ number of events (rows). field cardinality is FREE.
   group by user.id    → fine    group by trace_id → fine    filter user.id = 88142 → fine
```

| | **TSDB (metrics)** | **Wide-event store (observability)** |
|---|---|---|
| Aggregation | At write time (pre-aggregated) | At query time (raw events kept) |
| Cost driver | Cardinality of labels | Number of events |
| High-cardinality field | Catastrophic (series explosion) | The point (slice to one customer) |
| Answers | Known-unknowns, cheaply | Unknown-unknowns |
| Example | Prometheus | Honeycomb, ClickHouse-backed tracing |

### The worked example — finding the one affected customer

A customer (account 88142) reports failed checkouts. Your error-rate dashboard shows 0.3% — within the SLO, nothing fires. In a *metrics-only* world you are stuck: you cannot `group by user_id` because it was never a label. In a *wide-event* world:

```sql
-- Query the raw checkout events (e.g. Honeycomb, or ClickHouse over OTel spans)
SELECT payment.provider, build.version, COUNT(*) AS failures
FROM   checkout_spans
WHERE  http.status >= 500
   AND time > now() - INTERVAL 1 HOUR
GROUP BY payment.provider, build.version
ORDER BY failures DESC;
```

The result shows every failure is `payment.provider = "stripe-v2"` AND `build.version = "4.2.1"`. You filter to `account.id = 88142` and confirm they were routed to the new provider by a feature flag. Total time: three queries, no new instrumentation, no deploy. *That* is observability — and it was only possible because `payment.provider`, `build.version`, and `account.id` were captured as **high-cardinality attributes on the wide event**, the exact thing a TSDB would have forbidden.

---

## Designing Spans and the Data Model

This is the senior craft: shaping spans so the system answers future questions. The decisions are mostly irreversible without a deploy, so they must be made deliberately.

### Span granularity — what deserves a span

- **A span is a unit of work worth timing and worth attributing.** Inbound request, outbound call, DB query, queue publish, a meaningful domain operation ("evaluate fraud", "apply discount rules").
- **Don't over-span.** A span per loop iteration or per trivial function buries the signal and multiplies cost. Prefer a **span event** (a timestamped annotation inside a span) for checkpoints that don't need their own duration.
- **Don't under-span.** A single span for a 2-second handler that does three remote calls hides where the time went. Each external dependency gets its own span.

### Span naming — low cardinality, always

The span *name* is a low-cardinality dimension (it becomes a series in derived span-metrics). Use **route templates**: `GET /users/:id`, never `GET /users/88142`. The high-cardinality ID goes in an **attribute** (`user.id = 88142`), where it belongs. Getting this backwards re-creates the cardinality explosion inside your tracing backend's span-metrics.

### Attribute design — the part that decides 3 a.m.

The attributes you attach are the dimensions you can `group by` later. Capture, on the *entry* span of every request:

| Category | Examples | Why |
|---|---|---|
| **Identity** | `user.id`, `tenant.id`, `account.id`, `session.id` | Slice to the affected customer/tenant. |
| **Provenance** | `build.version`, `region`, `availability_zone`, `host.name`, `deployment.env` | "Which build / region regressed?" |
| **Business shape** | `customer.plan`, `cart.value`, `payment.provider`, `feature.flags` | The dimensions incidents actually correlate with. |
| **Mechanics** | `retry.count`, `cache.hit`, `db.pool.wait_ms`, `queue.lag_ms` | Distinguish causes that look identical from outside. |

The test for whether an attribute earns its place: **"Could a future incident be explained by grouping on this field?"** If yes, it's worth the bytes. If it's just decoration, drop it.

### The wide-event discipline

Push attributes onto **one wide span per operation** rather than scattering them across many narrow spans or separate log lines. Many backends let you "BubbleUp" / run outlier analysis: given a slow or erroring subset, automatically surface which attribute values are over-represented. That analysis is only as good as the width of your events — every attribute you didn't capture is a dimension the tool can't suggest.

### Semantic conventions, then your namespace

Use OTel **semantic conventions** for standard things (`http.request.method`, `db.system`, `db.statement`, `messaging.system`) so backends auto-recognise them. Put your domain attributes in a clear, owned namespace (`app.cart.value`, `app.fraud.score`) to avoid collisions and signal intent.

---

## Correlating the Signals, Deeply

Correlation is what turns four signals into one observable system. Each link is *engineered*; none is free. The senior nuance is knowing *how* each link is implemented and where it silently breaks.

### metric → trace, via exemplars

An **exemplar** is a `trace_id` (and span_id) attached to a specific metric data point — concretely, to a histogram bucket observation. When a latency histogram shows a spike in the 2-5s bucket, the exemplar lets you jump to *an actual trace that landed in that bucket* — not "a trace from around then," but a request that produced that exact data point.

The senior gotcha: an exemplar only attaches if the metric is recorded **inside an active span**, because the SDK reads the current `trace_id` at record time. Record your histogram observation where the span is current, or the exemplar is empty. Also: exemplars respect sampling — if the linked trace was sampled out, the exemplar points at nothing. Wire tail sampling so error/slow traces (the ones exemplars point to) are retained.

### trace → log, via `trace_id` in logs

Stamp `trace_id` and `span_id` on every log line (via an OTel log handler or a logging hook that reads the active context). From any span you can then pull every log emitted during it, and from any log line you can jump to the full trace. The break here is **format mismatch**: emit the `trace_id` as the standard 32-hex-char value; if your logger truncates it or formats it differently than the backend expects, the join silently returns nothing.

### trace → profile, via span context

The newest link: a **span-aware continuous profiler** tags CPU/alloc samples with the active `span_id`, so for one slow span you can ask "which function was burning CPU *for this request*?" (cross-ref [continuous-profiling](../12-continuous-profiling/README.md)). This closes the loop from "this request was slow" to "this line of code was the reason."

```text
[metric spike] ──exemplar(trace_id)──► [trace: the slow span]
                                            │
                              trace_id ─────┼───── span_id
                                            ▼            ▼
                                      [logs for      [profile: hot
                                       this request]   funcs in span]
```

Build all four links *before* the incident. The teams that debug in minutes are the ones for whom every arrow already exists.

---

## The Observability-Driven Debugging Loop

Observability is a *method*, not just data. The loop:

```text
   ┌────────────────────────────────────────────────────┐
   │  1. OBSERVE   a symptom (alert, SLO burn, report)   │
   │  2. HYPOTHESISE a cause ("maybe the new provider")  │
   │  3. QUERY     the wide events to test it (group by) │
   │  4. NARROW    on what the data shows (eu-west only) │
   │  5. REPEAT    until the cause is isolated           │
   │  6. CONFIRM   the fix by re-querying                │
   └────────────────────────────────────────────────────┘
```

The key property: **each step is a query against existing data, not a code change.** You form a hypothesis ("enterprise customers only"), test it (`group by customer.plan`), and either confirm or pivot — *in seconds*, repeatedly, until the cause is cornered. This is the opposite of "add a log line, redeploy, wait for it to recur" — the loop that takes days.

Compare the two debugging modes:

| | **Monitoring-driven (slow)** | **Observability-driven (fast)** |
|---|---|---|
| Start | A dashboard looks wrong | A symptom + a hypothesis |
| To investigate | Add a log line, deploy, wait | Run a query |
| To narrow | Guess, repeat the deploy cycle | `group by` the next dimension |
| Time to cause | Hours to days | Minutes |
| Requires | Reproducing the bug | Only that the data was captured |

The loop is only fast if the data model supports it — which is why span/attribute design (above) is *the* enabling investment.

---

## SLIs, SLOs & Error Budgets — The User-Facing Layer

Observability lets you debug; **SLOs decide what to debug and when to act.** They are the user-facing layer computed from the same telemetry. (Mechanics live in engineering-metrics-and-dora; here we connect them to observability design.)

- **SLI (Indicator):** a measured ratio of *good events / valid events* — e.g. `(requests with status < 500 AND latency < 300ms) / (all valid requests)`. Crucially, **the SLI is a query over your wide events.** If you designed events well, your SLI is just a filter; if you didn't, you can't even define a good SLI.
- **SLO (Objective):** the target — e.g. 99.9% of checkouts succeed within 300ms over 28 days.
- **Error budget:** `1 − SLO` = the allowed failure. 99.9% over 28 days ≈ 40 minutes of budget. Burn it slowly and all is well; burn it fast and you stop shipping features and fix reliability.

The senior insight: **measure the SLI from the user's perspective**, which usually means span-derived, request-level success — not a server-side resource metric. "CPU < 80%" is not an SLI; "checkout p99 < 300ms" is. And split success vs error latency so a flood of fast 500s can't flatter the percentile (a fast failure is still a failure). Error budgets are also what make **alerting humane**: alert on *budget burn rate*, not on every threshold blip — page when you'll exhaust the budget soon, not when a single data point wobbles.

---

## Trace-Based vs Metric-Based Alerting

Alerting strategy is a senior design decision. The two modes complement each other.

| | **Metric-based alerting** | **Trace/event-based alerting** |
|---|---|---|
| Fires on | Aggregate threshold / SLO burn | Patterns in raw events (e.g. "any trace with `payment.provider=stripe-v2` AND error") |
| Strength | Cheap, fast, stable; great for SLOs | Catches narrow, high-cardinality conditions metrics can't express |
| Weakness | Blind to high-cardinality slices | More expensive; can be noisy |
| Use for | The reliable, predictable floor (SLO burn, saturation) | Targeted conditions: a specific tenant, a specific build regressing |

**The strategy:** alert on **SLO burn rate** (metric/aggregate) for the reliable floor — multi-window, multi-burn-rate alerts so you page on a real budget threat, not noise. Use **trace/event-based** alerts for the narrow conditions metrics fundamentally cannot see (a single high-value tenant erroring, a new build's error rate spiking only in one region). Critically: **fewer, better alerts.** Every alert that doesn't lead to action is alert fatigue — see the `monitoring-alerting` skill. The wide-event model lets you investigate the long tail *without* an alert for every slice; reserve alerts for "a human must act now."

---

## Sampling and Fidelity

Sampling is the lever between cost and **fidelity** — how faithfully your stored telemetry reflects reality. (Deep dive: [telemetry-cost](../14-telemetry-cost-and-sampling-strategy/README.md).) The senior framing:

- **Head sampling** decides at trace *start* (and propagates the decision). Cheap and simple, but you decide *before* knowing if the trace is interesting — so naïve head sampling at 1% keeps 1 in 100 errors, and the rare failure is exactly what you wanted.
- **Tail sampling** decides at trace *end*, in the Collector, after seeing the whole trace. You can keep **100% of errors and slow traces** and sample the boring fast majority. The cost: the Collector must buffer whole traces in memory until they complete, which constrains topology (covered in [`professional.md`](professional.md)).

The fidelity principle: **never sample away the rare thing you'll need.** Allocate fidelity to errors, latency outliers, and high-value tenants; spend cheap on the boring successful majority. And remember the metric/event asymmetry: **metrics are aggregates and need no sampling** (a counter counts everything cheaply); it's the *per-event* traces and logs that you sample. So a sound design keeps full-fidelity SLO metrics *and* tail-sampled high-fidelity traces — the metric tells you something is wrong, the retained error traces tell you why.

> **Sampling and SLOs interact:** compute SLIs from *unsampled* metrics (or from counts before sampling), never from sampled traces — or your error rate is wrong by your sampling factor.

---

## Debugging in Production

The whole point. (Cross-ref [testing-in-production](../../testing/13-testing-in-production/README.md) — observability is its prerequisite; you can't safely test in prod if you can't see what happens.)

- **Production is the only complete environment.** Staging lacks real traffic shapes, real cardinality, real concurrency, real data. The unknown-unknowns live in prod, so observability must be a prod-first capability.
- **The loop runs against live data.** Hypothesis → query the last hour of wide events → narrow → confirm. No reproduction, no redeploy.
- **Feature flags + observability = controlled prod debugging.** Flip a flag for 1% of traffic, slice the wide events by `feature.flag`, compare error/latency for the flagged cohort. You're running an experiment in production with the safety of observability.
- **Correlate, don't guess.** From an SLO burn → exemplar to a slow trace → logs for that request → profile of the hot span. The chain is the method.
- **Capture the request identity** so a customer report ("order #X failed at 14:03") becomes a query, not a fishing expedition. This is why `order.id`, `request.id`, `account.id` belong on the wide event.

---

## Code Examples

### Go — a wide span: business attributes, error status, span event, exemplar-friendly metric

```go
import (
	"context"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/codes"
	"go.opentelemetry.io/otel/metric"
	"go.opentelemetry.io/otel/trace"
)

var (
	tracer        = otel.Tracer("checkout")
	checkoutDurMs metric.Float64Histogram // created at init; exemplars auto-attach
)

func Checkout(ctx context.Context, req CheckoutReq) (err error) {
	// One WIDE span for the operation: dense in the dimensions a 3 a.m. query needs.
	ctx, span := tracer.Start(ctx, "checkout.process")
	defer span.End()
	span.SetAttributes(
		// identity (high-cardinality — fine on a span/event, forbidden as a TSDB label)
		attribute.String("app.account.id", req.AccountID),
		attribute.String("app.user.id", req.UserID),
		// business shape — the dimensions incidents correlate with
		attribute.String("app.customer.plan", req.Plan),
		attribute.Float64("app.cart.value", req.CartValue),
		attribute.String("app.payment.provider", req.Provider),
		attribute.Bool("app.feature.new_checkout", req.NewCheckoutFlag),
	)

	start := nowMs()
	if err = charge(ctx, req); err != nil {
		span.RecordError(err)                          // failure shows in the trace...
		span.SetStatus(codes.Error, "charge failed")   // ...and in span-derived error metrics
		span.AddEvent("charge.declined",               // span event: cheaper than a child span
			trace.WithAttributes(attribute.String("decline.code", declineCode(err))))
	}
	// Record the histogram INSIDE the active span so the exemplar carries this trace_id.
	checkoutDurMs.Record(ctx, nowMs()-start,
		metric.WithAttributes(attribute.Bool("ok", err == nil))) // split success/error latency
	return err
}
```

### Python — `trace_id` in structured logs (the trace↔log link)

```python
import logging, json
from opentelemetry import trace

class TraceContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        ctx = trace.get_current_span().get_span_context()
        # standard 32-hex / 16-hex formatting — MUST match what the backend expects
        record.trace_id = format(ctx.trace_id, "032x") if ctx.is_valid else ""
        record.span_id = format(ctx.span_id, "016x") if ctx.is_valid else ""
        return True

class JsonFormatter(logging.Formatter):
    def format(self, r: logging.LogRecord) -> str:
        return json.dumps({
            "level": r.levelname, "msg": r.getMessage(),
            "trace_id": getattr(r, "trace_id", ""),
            "span_id": getattr(r, "span_id", ""),
        })

log = logging.getLogger("checkout")
h = logging.StreamHandler(); h.addFilter(TraceContextFilter()); h.setFormatter(JsonFormatter())
log.addHandler(h)
# Now: {"level":"ERROR","msg":"charge failed","trace_id":"7c1e...","span_id":"aaaa..."}
# From the trace you pull these logs; from a log line you jump to the trace.
```

### A wide structured event (what one checkout looks like as a row)

```json
{
  "trace_id": "7c1ea9f3b2d4...", "span_id": "aaaa1111...", "name": "checkout.process",
  "duration_ms": 2841, "http.status": 500, "http.route": "POST /checkout",
  "app.account.id": "88142", "app.user.id": "u_91022", "app.customer.plan": "enterprise",
  "app.cart.value": 1299.00, "app.payment.provider": "stripe-v2", "app.fraud.score": 0.07,
  "region": "eu-west-1", "availability_zone": "eu-west-1b", "host.name": "checkout-7d9c-x2",
  "build.version": "4.2.1", "app.feature.new_checkout": true,
  "db.pool.wait_ms": 12, "cache.hit": false, "retry.count": 1, "decline.code": "provider_timeout"
}
```

Forty fields on one event. `group by build.version, payment.provider WHERE http.status >= 500` corners the incident — and every field that *could* be a `group by` was a deliberate design choice.

### OTel Collector — tail sampling tuned for fidelity (keep what you'll need)

```yaml
processors:
  tail_sampling:
    decision_wait: 12s            # buffer whole traces this long before deciding
    policies:
      - name: keep-all-errors     # 100% fidelity on failures
        type: status_code
        status_code: { status_codes: [ERROR] }
      - name: keep-slow           # 100% fidelity on latency outliers
        type: latency
        latency: { threshold_ms: 1000 }
      - name: keep-high-value     # never sample away a key tenant
        type: string_attribute
        string_attribute: { key: app.customer.plan, values: [enterprise] }
      - name: sample-the-boring   # spend cheap on the successful majority
        type: probabilistic
        probabilistic: { sampling_percentage: 3 }
```

This config *is* the fidelity-allocation decision made concrete: full fidelity on errors, slow traces, and enterprise customers; 3% on everything else.

---

## Best Practices

1. **Design wide entry spans.** Identity + provenance + business shape on every request's top span — these are the dimensions 3 a.m. needs.
2. **High cardinality on events, never on TSDB labels.** `user.id` is gold on a span, poison as a Prometheus label.
3. **Low-cardinality span *names* (route templates); high-cardinality detail in attributes.** Don't recreate the explosion in your tracing backend.
4. **Record metrics inside the active span** so exemplars carry the `trace_id`.
5. **Stamp `trace_id`/`span_id` on every log** in the exact format the backend expects.
6. **Define SLIs as request-level user-perceived success**, split success/error latency, alert on burn rate.
7. **Tail-sample for fidelity:** keep all errors, slow traces, and key tenants; sample the boring majority; keep metrics unsampled.
8. **Build all correlation links before the incident** — metric→trace→log→profile.
9. **Fewer, actionable alerts.** If it doesn't demand human action now, it's a query, not an alert (see `monitoring-alerting`).
10. **Capture request identity** so a customer report becomes a query, not a hunt.

---

## Edge Cases & Pitfalls

- **The fast-failure that flatters p99.** A flood of 2ms 500s drags overall latency *down* while users scream. Split duration by status class.
- **Cardinality explosion in the *tracing* backend** from high-cardinality span *names* (`GET /users/12345`). Use route templates; ID in attributes.
- **Empty exemplars.** Metric recorded outside an active span, or the linked trace was sampled out. Record in-span; retain error/slow traces.
- **Silent trace↔log join failure** from `trace_id` format mismatch (truncated, wrong case, wrong length). Emit standard 32-hex consistently.
- **SLIs computed from sampled traces** — your error rate is off by the sampling factor. Compute SLIs from unsampled metrics/counts.
- **Tail sampler memory blowup** on very long traces — the Collector buffers whole traces; a 30-minute trace pins memory. Cap span/trace duration; size the Collector.
- **Resource attributes as a hidden cardinality bomb.** `host.name` per pod in a huge fleet multiplies metric series; fine on events, dangerous as metric labels.
- **Attributes that decorate but never get queried** — pure cost. If no incident could be explained by grouping on it, drop it.

---

## Common Mistakes

1. **"We have logs, metrics, and traces, so we're observable."** Three silos with no shared identity answer nothing new. Correlation is the property.
2. **Putting high-cardinality fields on metric labels** and taking down Prometheus — when they belonged on the wide event.
3. **Narrow spans, no business attributes** — you can trace the plumbing but can't answer "which customer/plan/build."
4. **Debugging by add-log-line-and-redeploy** instead of querying existing wide events. Days instead of minutes.
5. **SLIs measured server-side** (CPU, queue depth) instead of user-perceived request success.
6. **Alerting on every threshold** instead of on error-budget burn — alert fatigue, and the real page gets lost.
7. **Random head sampling that eats errors** — the rare failure is the one you needed.
8. **Computing the SLO from sampled data** — wrong by the sampling factor.

---

## Tricky Points

1. **The same field is forbidden in metrics and mandatory in events.** `user.id`: one series per value (TSDB death) vs one filterable column (observability win). The split is write-time vs query-time aggregation.
2. **Exemplars depend on the metric being recorded inside an active span**, *and* on the linked trace surviving sampling. Two independent ways to get empty exemplars.
3. **A fast failure improves your latency percentile.** Speed and success are orthogonal; always split duration by status.
4. **SLIs must be unsampled, traces should be sampled.** Different fidelity needs for the same incident — metric says "wrong", retained error trace says "why".
5. **Span name cardinality bites the *tracing* backend** the same way label cardinality bites the TSDB — many backends derive span-metrics from names.
6. **Observability subsumes but doesn't replace monitoring.** You still want cheap pre-aggregated SLO/saturation alerts; you do not run a query to learn the disk is full.
7. **You can only group by what you captured.** No amount of clever querying recovers a dimension you never put on the event.

---

## Apply it

1. State the system invariant that **Observability Engineering** must protect.
2. Mark ownership, state, and failure propagation at each boundary.
3. Compare two designs under load, dependency failure, and future change.
4. Define recovery and compatibility behavior before implementation.
5. Test the riskiest assumption with a focused experiment.

## Verify your work

- The experiment supports the design with evidence, not preference.
- Failure injection shows the blast radius and recovery path.
- Compatibility checks cover old and new callers or data.
- Operational signals reveal invariant violations and recovery progress.

## Review questions

- Which invariant must remain true when Observability Engineering fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
