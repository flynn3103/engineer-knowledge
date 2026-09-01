# Metrics — Professional (Staff / Principal) Level

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Metrics — Professional (Staff / Principal) Level** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Topic:** [Metrics Roadmap](README.md)
> **Focus:** The metrics *emission* layer as a fleet-wide engineering substrate. OpenTelemetry's metrics architecture — instruments, views, readers, exporters, temporality — as the contract you design across dozens of services and five languages. Exemplars that wire a histogram bucket to a trace. Cardinality control and cost as a budget enforced *in the SDK*, before a byte leaves the process. Push vs pull when "the fleet" is the unit, not "the service."

---

## Core Concepts

### 1. The instrument *type* is a contract, chosen once, irreversible without a migration

When you pick `Histogram` over `Gauge`, or `Counter` over `UpDownCounter`, you are not choosing an API convenience — you are fixing the **default aggregation, the monotonicity guarantee, and the temporality semantics** for the lifetime of that metric. A counter that should have been an up-down counter corrupts every `rate()`. A gauge that should have been a histogram throws away the distribution forever. The type is the first and most expensive design decision, and at fleet scale it must be *the same type for the same concept in every language*.

### 2. The View is where the fleet's policy becomes code

OTel's **View** is the single most under-used feature in the ecosystem and the most important one at this level. It is the in-SDK control plane: it can drop a high-cardinality attribute, force exponential histograms across every duration instrument, rename an instrument to match semconv, or impose a cardinality limit — all *before* the exporter sees a byte. Everything you wished you could enforce in a wiki, you enforce in a View. **A fleet without a standard View configuration is a fleet hoping every engineer reads the wiki.**

### 3. Temporality is a property of the *process lifetime crossed with the backend*, and it's set at emit time

Cumulative is correct for a long-lived process feeding a Prometheus-style backend. Delta is correct for a serverless invocation, for a memory-constrained sidecar, and for backends that natively want delta. The trap is that the SDK *default* differs by language and exporter, so a fleet that doesn't standardize temporality ends up with the same metric meaning different things in different services. This is a code-level decision you must make explicitly and uniformly.

### 4. Exemplars are the highest-leverage emit-side feature of the last five years

An aggregated metric throws away identity by design — that's what makes it cheap. An exemplar smuggles *one* identity (a trace ID) back onto an aggregated point. With exemplars, "p99 latency spiked at 14:32" becomes a clickable link to the exact trace of one of those slow requests. Without them, you're back to grepping logs by timestamp. Exemplars are configured in the SDK (the `ExemplarFilter` and `ExemplarReservoir`) and require trace context to be active — they are a metrics+traces co-design, not a metrics-only feature.

### 5. Cardinality must be capped *in the SDK*, because the collector is too late and the wiki is too weak

There are three places to control cardinality: in the application code (allow-lists at the call site), in the SDK (Views + cardinality limits), and in the pipeline (collector/relabel). The SDK is the *most reliable* one that's still in your repo: a `View` with a cardinality limit turns an unbounded `user_id` attribute into a bounded, observable `otel.metric.overflow` point — the bomb defuses itself, in code you control, before OTLP export. The collector catches what the SDK missed; the wiki catches nothing.

### 6. Every metric has a recurring, multi-dimensional bill, and at fleet scale the bill is real money

Senior level taught "cardinality is a budget." Professional level *prices* it: active series → TSDB RAM and disk; datapoints/minute → SaaS billing; export frequency × payload size → network egress; instrument count × attribute count → CPU in the SDK's aggregation. A single unbounded attribute on a hot instrument across 200 pods can add hundreds of thousands of series and a five-figure annual bill. You design the emission to fit a *priced* budget, not just a series count.

### 7. Push vs pull at fleet scale is a control-plane decision about *where cardinality and discovery live*

For one service it's an operational preference. For a fleet it determines where you can *enforce* limits (scrape relabel vs collector pipeline vs SDK), how you detect liveness across hundreds of ephemeral targets, and whether a single bad service can flood a shared collector. The modern answer is almost always **OTLP push to a per-node/per-cluster collector**, which then either remote-writes or is scraped — centralizing control while keeping the app's transport simple. You design that topology; you don't inherit it.

---

## The OpenTelemetry Metrics Pipeline

Everything in this page hangs off one mental model: the OTel metrics SDK is a **pipeline**, and you control every stage. Understanding *which stage does what* is the difference between "I added a label and the bill exploded" and "the View drops that attribute before it can become a series."

```text
   APP CODE                SDK (in-process)                         WIRE
   ────────                ────────────────                         ────
   instrument.Record(v, attrs)
        │
        ▼
   ┌──────────┐   ┌────────┐   ┌─────────────┐   ┌──────────┐   ┌──────────┐
   │ Instrument│─▶│  View  │─▶│ Aggregation │─▶│  Reader  │─▶│ Exporter │─▶ OTLP / Prom
   │  (API)    │   │(rewrite│   │ (sum / hist │   │(periodic │   │(serialize│
   │           │   │ /drop/ │   │  / lastval) │   │ or pull) │   │ + tempor)│
   │           │   │ limit) │   │ + exemplars │   │          │   │          │
   └──────────┘   └────────┘   └─────────────┘   └──────────┘   └──────────┘
        │              │              │                │              │
   type fixes     fleet policy   cardinality &    push cadence    temporality
   semantics      lives here     exemplar         or scrape       + format
                                 reservoir live   trigger         chosen here
```

| Stage | What you decide | Where it lives in code |
|-------|-----------------|------------------------|
| **Instrument** | Type (counter/histogram/gauge/…), name, unit, description | The `meter.NewX(...)` call |
| **View** | Rename, change aggregation, keep/drop attributes, set buckets, cardinality limit | `WithView(...)` on the provider |
| **Aggregation** | Sum vs explicit-bucket histogram vs exponential histogram vs last-value | Default by instrument type, overridable in the View |
| **Reader** | Push (periodic, with interval) vs pull (Prometheus scrape triggers collect) | `WithReader(NewPeriodicReader(...))` or the Prometheus exporter |
| **Exporter** | OTLP gRPC/HTTP vs Prometheus exposition; **temporality preference** | The exporter constructor |
| **Resource** | `service.name`, `service.version`, `deployment.environment` on *every* point | `WithResource(...)` |

The crucial property: **each stage is configured once, at provider construction, and applies to every instrument in the process.** This is why the fleet standard is a *provider-construction standard* — a shared `initMetrics()` function or library that every service calls, not a per-instrument convention nobody follows.

---

## Instruments — The Full Taxonomy

Senior level dealt mostly with counters and histograms. At professional level you need the *whole* instrument set, because choosing the wrong one is a fleet-wide correctness bug, and the synchronous/asynchronous split has real performance and correctness consequences.

| Instrument | Monotonic? | Sync/Async | Default aggregation | Use it for | Prometheus mapping |
|------------|-----------|------------|---------------------|------------|--------------------|
| **Counter** | Yes (↑ only) | Sync | Sum | Requests, bytes, errors — things that only accumulate | `_total` counter |
| **UpDownCounter** | No (↑/↓) | Sync | Sum (non-monotonic) | Queue depth, active connections, in-flight requests | gauge |
| **Histogram** | n/a | Sync | Explicit-bucket histogram | Latency, payload size — distributions | `_bucket`/`_sum`/`_count` |
| **Gauge** | No | Sync (OTel 1.23+) | Last value | Instantaneous measured values recorded at the call site | gauge |
| **ObservableCounter** | Yes | Async (callback) | Sum | Cumulative values you read on demand (CPU seconds from `/proc`) | `_total` counter |
| **ObservableUpDownCounter** | No | Async | Sum (non-monotonic) | A value you poll that can go up/down (pool size) | gauge |
| **ObservableGauge** | No | Async | Last value | A value you sample in a callback (temperature, queue length read at collect) | gauge |

### The sync/async distinction is a correctness decision, not a style one

**Synchronous** instruments record at the moment something happens, in the request path — `counter.Add(1, attrs)` inside the handler. **Asynchronous (observable)** instruments register a *callback* that the SDK invokes at collection time; the callback reports the current value. The rules that bite:

- **Async callbacks must be cheap and side-effect-free** — they run on the SDK's collection thread on every collection cycle (every scrape, every push interval). A callback that hits the database is a self-inflicted load spike synchronized to your scrape interval. (This is the "vanity gauge recomputed every scrape" anti-pattern from senior level, now with a name.)
- **An async instrument reports the *last* value per attribute set per collection** — if your callback reports the same attribute set twice in one cycle, the SDK keeps the last. Don't loop and double-report.
- **Use async for "what is the value *right now*"** (pool size, queue depth read once at collect). **Use sync for "an event happened"** (a request, an error, a byte transferred). Picking sync for a sampled value, or async for an event count, is a classic miscategorization.

### The `Gauge` vs `UpDownCounter` confusion (a fleet-wide footgun)

Both map to a Prometheus gauge, so engineers assume they're interchangeable. They are not:

- **`UpDownCounter`** carries *deltas* you `Add(+1)`/`Add(-1)` at events (connection opened / closed). The SDK maintains the running value. Aggregatable as a sum across instances.
- **`Gauge`** (or `ObservableGauge`) carries an *absolute measured value* (current temperature, current pool size). **Summing gauges across instances is usually meaningless** (you don't `sum()` temperatures), whereas summing up-down counters across instances *is* meaningful (total connections fleet-wide).

Standardize this in your fleet doc: *"in-flight / active / depth that you increment and decrement at events → `UpDownCounter`; a value you sample → `Gauge`/`ObservableGauge`."* Getting it wrong produces dashboards that look right per-pod and lie when aggregated.

---

## Views — The SDK's Control Plane

A **View** is a rule: *match these instruments, transform their stream this way.* It is the single most powerful emit-side governance tool, and at fleet scale it is where your standards stop being prose and start being enforced code. Five things a View does, each a fleet policy:

| View capability | Fleet policy it enforces |
|-----------------|--------------------------|
| **Drop / keep attribute keys** | "`user_id` is *never* a metric attribute" — strip it in the SDK so it can't become a series. |
| **Set explicit or exponential buckets** | "Every duration instrument is a base-2 exponential histogram" — uniform accuracy, ~1 series, no per-service bucket disagreement. |
| **Rename instrument / change unit** | "Legacy `request_time_ms` is exposed as `http.server.request.duration` in seconds" — migrate without touching call sites. |
| **Change aggregation** | "Drop this expensive instrument to `Drop` aggregation in prod, keep it in staging" — kill a metric without redeploying the emitting code. |
| **Cardinality limit** | "No instrument may exceed 2,000 attribute sets; overflow collapses to `otel.metric.overflow`" — the bomb defuses itself. |

### The drop-attribute View is your first line of cardinality defense

```go
// OTel Go — a View that keeps ONLY the bounded attributes on a hot instrument.
// user_id, request_id, session_id never survive to become series.
metric.NewView(
    metric.Instrument{Name: "http.server.request.duration"},
    metric.Stream{
        AllowAttributeKeys: attribute.NewSet(
            attribute.String("http.request.method", ""),
            attribute.String("http.route", ""),
            attribute.String("http.response.status_code", ""),
        ),
    },
)
```

`AllowAttributeKeys` is an allow-list, not a deny-list, on purpose: a deny-list is a game of whack-a-mole where the next engineer adds `tenant_id` and you didn't deny it yet. An allow-list fails *closed* — anything you didn't explicitly permit is dropped. **At fleet scale, allow-lists are the only safe cardinality posture.**

### The cardinality-limit View turns an OOM into a metric

```go
// OTel Go (≥ v1.28 cardinality limits via View, or SDK-level limit).
// When an instrument exceeds the limit, excess attribute sets collapse to
// a single point with attribute {"otel.metric.overflow": "true"}.
metric.NewView(
    metric.Instrument{Name: "db.client.operation.duration"},
    metric.Stream{
        AggregationCardinalityLimit: 2000,
    },
)
```

The overflow point is itself a signal: alert on `otel_metric_overflow` (or your backend's equivalent of the overflow attribute) and you find out *which instrument* is leaking the moment it crosses the limit — instead of finding out via a TSDB OOM at 3 a.m. This is the senior "make the bomb page you, not OOM you" principle, now implemented in the SDK rather than the scrape config.

### Views are why migrations are possible without coordinated deploys

The killer use of Views at fleet scale: you can **change what's exported without changing the code that records.** A legacy service records `http_request_ms` in milliseconds; semconv wants `http.server.request.duration` in seconds. A View renames it, converts the unit via re-bucketing, and the dashboards migrate while the application code stays put until a convenient refactor. This decouples *the instrumentation standard* from *the deploy schedule* — essential when you're migrating forty services.

---

## Readers, Exporters, and Temporality at the Edge

The **Reader** drives collection; the **Exporter** serializes it; **temporality** is the semantic glue, set on the exporter. At fleet scale these three decisions, made at provider construction, determine your transport, your cost, and whether your data is even *correct* for the backend it lands in.

### Push (PeriodicReader) vs pull (Prometheus exporter)

```text
   PeriodicReader  →  collect every N seconds  →  OTLPExporter  →  collector / backend   (PUSH)
   Prometheus exporter  →  collect ON scrape    →  exposition over /metrics              (PULL)
```

- **PeriodicReader + OTLP** is push: the SDK collects on a timer and ships. You choose the interval (a cost lever — see below) and the temporality.
- **The Prometheus exporter is pull**: it's a `Reader` that collects *when scraped*. Temporality is forced **cumulative** (Prometheus's model); you don't get to choose delta here.

### Temporality is set per instrument-kind, per exporter

The OTLP exporter takes a **temporality preference**. The three standard presets:

| Preset | Counter / Histogram | UpDownCounter | When |
|--------|--------------------|---------------|------|
| **Cumulative** | cumulative | cumulative | Prometheus/Mimir/Thanos backends; long-lived processes |
| **Delta** | delta | cumulative* | Datadog, serverless, memory-constrained; FaaS |
| **LowMemory** | delta histogram, cumulative sum | cumulative | Trim histogram memory in long-lived processes while keeping sums Prometheus-friendly |

\* UpDownCounters stay cumulative even in delta mode because a "delta of a gauge-like value" is rarely meaningful.

**The fleet trap:** Java's OTel SDK and the Go SDK default differently, and the Prometheus exporter forces cumulative regardless. If half your fleet pushes delta to a collector that does `delta-to-cumulative` and the other half pushes cumulative, the *same metric* has two reset behaviors. **Standardize temporality at the fleet level and set it explicitly in every `initMetrics()`** — never rely on the SDK default, because the default is not the same across languages.

### The export interval is a cost and correctness lever

For a `PeriodicReader`, the export interval (default 60s in OTel, often dropped to 10–15s) controls:

- **Cost:** datapoints/minute scales inversely with interval. A 10s interval is 6× the DPM of a 60s interval — directly 6× the bill on a DPM-priced backend (Grafana Cloud) for the same metrics.
- **Resolution:** a 60s interval can't show a 20s spike. Your interval must be ≤ half the smallest event you need to see (Nyquist, informally).
- **Delta data loss:** with delta temporality, a dropped export *loses that interval's increments forever* (no running total to recover from). Longer intervals = more data at risk per drop. This pushes delta deployments toward shorter intervals with reliable transport.

The interval is a per-process decision you standardize, and you tune it against the backend's pricing unit, not just "feels frequent enough."

---

## Exemplars — Linking Metrics to Traces

This is the professional-tier feature that doesn't exist at senior level, and it is the single biggest workflow improvement in metrics emission in the last five years. An **exemplar** is a raw sample measurement, attached to an aggregated metric point, that carries the **trace ID and span ID** that were active when the measurement was recorded (plus a small set of filtered attributes and a timestamp).

The payoff: a "p99 latency = 4.2s" point on a Grafana panel becomes a **clickable link to the actual trace** of one of the requests that landed in that bucket. You go from "the 99th percentile is bad" to "*here is the exact slow request and its full waterfall*" in one click — collapsing the metrics→traces→logs descent (see the [Debugging professional](../01-debugging/professional.md#the-observability-triangle-as-a-debugging-interface) triangle) from minutes of correlation to a single hop.

### How exemplars work at the SDK level

```text
   handler records histogram.Record(0.42, attrs)   ← a span is active in context
                          │
                          ▼
              ExemplarFilter decides: is this sample exemplar-worthy?
                          │  (trace_based → only if the span is SAMPLED)
                          ▼
              ExemplarReservoir stores it on the matching bucket
                          │  (fixed-size, per-bucket reservoir sampling)
                          ▼
              On export: bucket point carries {value, trace_id, span_id, ts, filtered_attrs}
```

Two SDK knobs you must understand:

- **`ExemplarFilter`** — `trace_based` (default and correct: only record exemplars for measurements taken under a *sampled* span, so the trace ID actually resolves to a stored trace), `always_on` (every measurement is exemplar-eligible — more exemplars, but many point at unsampled traces you can't open), `always_off` (disable). **`trace_based` is the fleet default**; `always_on` only makes sense if you sample traces at 100% or tail-sample.
- **`ExemplarReservoir`** — how many exemplars are kept per aggregation point per collection (a small fixed number, reservoir-sampled). You rarely tune this, but know it's bounded — exemplars are *sampled*, not exhaustive.

### Exemplars require the metric record to happen *inside* a span

This is the co-design constraint that bites teams: an exemplar can only capture a trace ID if **trace context is active in the current context/thread-local when `Record` is called.** If your metric recording happens outside the span scope (in a background flusher, after the span ended, on a different goroutine without context propagation), the exemplar has no trace ID and is useless. **Record metrics in the same context where the span is active.**

### Exemplars in the Prometheus exposition format

Prometheus carries exemplars on the OpenMetrics exposition format, appended to a bucket line after a `#`:

```text
http_request_duration_seconds_bucket{le="0.5"} 4823 # {trace_id="a1b2c3...",span_id="d4e5f6..."} 0.42 1700000000.123
```

For this to flow end-to-end you need: the client emitting exemplars (prom-client, client_golang with `ObserveWithExemplar`, OTel SDK with exemplar filter), the scrape configured with the OpenMetrics `Accept` header and `--enable-feature=exemplar-storage`, and Grafana wired to a trace datasource for the click-through. **Like native histograms, exemplars need every link in the chain or they silently vanish** — the client emits them and the scrape drops them if OpenMetrics negotiation isn't enabled.

### The cost/benefit framing

Exemplars add a small, bounded payload to each histogram (a handful per series), so the cost is negligible relative to the series themselves. The benefit — eliminating the "find the trace that matches this timestamp" archaeology — is enormous. **If your stack supports them, turning exemplars on for every latency histogram is one of the highest-leverage, lowest-cost changes you can make.** It is a pure emit-side win configured in the SDK.

---

## Cardinality Control at Fleet Scale

Senior level: a cardinality budget you enforce for *one service* at three layers. Professional level: cardinality is a **fleet-wide governed resource**, the SDK is your primary enforcement point (because it's the one in your repo, before export), and you design for the *aggregate* of forty services sharing one TSDB.

### The five enforcement layers, ordered by reliability

```text
1. CALL SITE        → allow-list label values in code; overflow → "other"     (cheapest, leakiest — humans forget)
2. SDK VIEW         → AllowAttributeKeys + AggregationCardinalityLimit         (in your repo, before export — MOST reliable in-code)
3. RESOURCE         → bound service.name/version/instance.id at process start  (Resource attrs multiply EVERY series)
4. COLLECTOR        → OTel transform/filter processors, attribute limits       (catches cross-service leaks; not in app repo)
5. BACKEND          → per-tenant active-series limits, scrape relabel drops    (last resort; rejects writes — data loss)
   + GLOBAL ALERT on total active series, per-metric series, AND churn rate
```

The professional insight: **layer 2 (the SDK View) is the one you should lean on hardest**, because it lives in the same repository as the code that creates the bomb, it applies uniformly via your shared `initMetrics()`, and it acts before any byte is exported — so it costs the collector and backend *nothing*. Layers 4 and 5 are real but they are *someone else's pipeline*, and by the time data reaches them the cardinality is already minted.

### Resource attributes are a silent multiplier

A subtle fleet-scale trap: **Resource attributes are attached to *every* metric the process emits.** Put `pod.name` or `instance.id` (which churns on every deploy/autoscale) in the Resource, and *every series from that process* gets a new identity on every roll. With 200 pods rolling daily, a single unbounded Resource attribute multiplies your *entire* series count and your churn. Keep the Resource to **bounded, slowly-changing** attributes: `service.name`, `service.version`, `service.namespace`, `deployment.environment`. Push `pod`/`instance`/`node` identity *out of the metrics* and into the collector's target labels or drop it — you almost never query a metric by pod, and when you do, it's a tracing/logging question.

### Churn is the cardinality cost nobody budgets for

Two fleets with identical *active* series counts can have wildly different TSDB index sizes if one churns. Every time a series is born (new `pod`, new `version`, new ephemeral attribute value), it enters the index *forever* within the retention window. A fleet that bakes `version` (changes per deploy) × `pod` (changes per roll) into series will mint thousands of dead series per day. **Budget churn explicitly** — alert on `rate(prometheus_tsdb_head_series_created_total[1h])`, not just current head series — and design Resource/attribute sets so a deploy doesn't reincarnate every series.

### The fleet-wide cardinality budget, allocated and enforced

A fleet budget is a *number*, allocated, with per-service caps enforced in the SDK:

```text
   TSDB capacity:        ~8M active series comfortable on the cluster
   Reserve (headroom):   30% → governable budget = 5.6M
   Per-service caps:     allocated by tier (a Tier-1 API gets 200k; a cron worker gets 5k)
   Enforced where:       SDK AggregationCardinalityLimit per instrument
                         + collector per-service drop rules
                         + backend per-tenant limit as the hard ceiling
   Alerted at:           80% of fleet budget; 80% of any per-service cap; any overflow point
```

The difference from senior level: you're not enforcing *one* budget, you're *allocating a fixed fleet capacity across teams* and giving each an SDK-level cap, so one team's mistake degrades to an overflow point instead of consuming the whole cluster's headroom.

---

## The Cost Model of a Metric

At professional level "cardinality is a budget" becomes "here is the literal bill." You must be able to price a proposed metric before it ships, because at fleet scale a single careless instrument is a five-figure line item.

### The four cost dimensions of emitted metrics

| Dimension | What drives it | Where it's paid |
|-----------|----------------|-----------------|
| **Active series** | name × distinct attribute sets × pods (after aggregation) | TSDB RAM + disk; the dominant cost on Prometheus-style backends |
| **Datapoints / minute** | active series ÷ export interval (in minutes) | Network egress; SaaS billing (Grafana Cloud DPM, Datadog) |
| **In-process CPU/RAM** | instrument count × attribute-set count × aggregation type (histograms are heavier) | The app's own footprint — the SDK aggregates in-process |
| **Custom-metric count** | unique metric-name × tag-set combinations | Datadog's headline billing unit; quota on Cloud Monitoring |

### A back-of-envelope cost calculation you should be able to do in your head

A new latency histogram on a Tier-1 API:

```text
   instrument:   http.server.request.duration  (classic histogram, 12 buckets)
   attributes:   method (5) × route (40) × status_class (5)   = 1,000 attribute sets
   buckets:      ×12 buckets (+ _sum + _count = +2)            = 14,000 series per pod
   pods:         ×150 pods                                     = 2,100,000 series  ⚠️

   → AFTER aggregating buckets at the collector / using native histograms:
   native histogram:  1,000 attribute sets × ~1 series × 150 pods = 150,000 series
   (a 14× reduction, same accuracy — the senior native-histogram lesson, now priced)
```

The classic histogram is **2.1M series**; the native/exponential equivalent is **~150k**. On a backend where 1M active series ≈ a few GB of RAM and a meaningful slice of a six-figure annual cluster cost, *that one choice* is the difference between "fine" and "a budget escalation." **This is why "prefer native histograms" stopped being a preference and became a cost-control mandate at fleet scale.**

### Pricing-unit awareness changes your emit-side design

| Backend | Billing unit | What you optimize at emit time |
|---------|--------------|--------------------------------|
| **Prometheus / Mimir / Thanos** | active series (RAM/disk) | Minimize distinct attribute sets; native histograms; drop pod identity |
| **Grafana Cloud** | datapoints/minute (DPM) | Lengthen export interval where resolution allows; reduce series |
| **Datadog** | custom metrics (unique name+tagset) | Ruthlessly bound tags; every distinct tag value is a billed custom metric |
| **GCP Cloud Monitoring** | per-metric-descriptor + ingestion quota | Bound label cardinality; quota rejects writes when exceeded |

The professional skill is knowing *which* of these your fleet lands in and designing the emission to its pricing unit. A team optimizing series count for a DPM-priced backend, or ignoring that Datadog charges per tag-value, is leaving money on the table or blowing the budget. **You price the metric in the unit that bills you, before you ship it.**

---

## Aggregation at the Source

The cheapest series is the one you never emit. **Source aggregation** — collapsing or pre-aggregating in the SDK before export — is how you cut cost without losing the signal you actually query. This is distinct from query-time aggregation (which is the backend's job and out of scope here); it's about what the *process* ships.

### What you can aggregate in the SDK

| Technique | What it does | Cost saved |
|-----------|--------------|------------|
| **Attribute dropping (View)** | Strip a dimension you never query, merging its series | Multiplicatively fewer series |
| **Bucketing low-stakes paths down** | Health-check / internal endpoints get `Drop` aggregation or a counter, not a histogram | Removes whole instruments |
| **Status-class instead of status-code** | `5xx` instead of `500/502/503/504` as four separate series | 4–5× fewer status series |
| **Route templates, not paths** | `/users/{id}` not `/users/12345` (unbounded → bounded) | Turns a bomb into ~1 series |
| **Native/exponential histograms** | One sparse series instead of N bucket series | ~order of magnitude per histogram |
| **Spatial pre-aggregation in a sidecar collector** | Sum across pods *before* hitting the central TSDB (drop `pod`) | Removes the pod multiplier |

### The "drop pod identity at the source" pattern

The most impactful source aggregation at fleet scale: **most metrics don't need per-pod resolution.** You almost never ask "what is pod `checkout-7f9-abc`'s p99?" — you ask "what is the *service's* p99?" So aggregate away the pod *before* central storage:

```text
   200 pods × 5,000 series/pod  =  1,000,000 series   ← per-pod, stored centrally (expensive, churny)

   per-node OTel collector sums across local pods, drops pod.name →
   ~5,000 series per service  ×  (number of distinct attribute sets)  ← spatially aggregated

   when you DO need per-pod (rare): keep it in logs/traces, or a short-retention high-res tier
```

The SDK-side half of this is *not putting pod identity in the Resource in the first place* (so it isn't on every series). The collector-side half (summing across pods) is downstream, but the emit-side decision — keep the Resource bounded — is what makes it possible. **If you bake `pod` into the series identity at emit time, no downstream aggregation can cheaply remove it.**

### When source aggregation is *wrong*

Source aggregation is lossy by design — you can't get back what you collapsed. Don't aggregate away a dimension you'll need:

- **A dimension that distinguishes a failure mode** (`error.type`, `db.operation`) — collapsing it blinds you during an incident.
- **The SLO dimension** — if your SLO is per-route, you can't drop `route`.
- **Anything an alert reads** — an alert on `route="/checkout"` errors needs `route` to survive.

The skill is dropping the *un-queried* dimensions (the ones that exist only because "it might be useful") while keeping the *load-bearing* ones. This is the senior "what not to measure" discipline applied to *dimensions of a metric*, not just whole metrics.

---

## Push vs Pull at Scale

Senior level framed pull vs push as a per-service architecture decision. At fleet scale it's a **control-plane topology** decision, and the answer for most modern fleets is a *hybrid*: the app pushes OTLP to a local collector, which then remote-writes (push) or is scraped (pull) by the backend. Understanding *why* requires seeing what each gives you at the scale of hundreds of targets.

| Concern at fleet scale | Direct pull (Prometheus scrapes apps) | Direct push (apps → backend) | **Hybrid (app → collector → backend)** |
|------------------------|---------------------------------------|------------------------------|----------------------------------------|
| Liveness | `up==0` per target, free | ambiguous silence → need heartbeats | collector liveness via pull; per-app heartbeat optional |
| Discovery | centralized in scraper (k8s SD) | every app must know the backend | app knows only the local collector (stable address) |
| Ephemeral / FaaS | dies before scrape | native | app pushes to collector, exits cleanly |
| Cardinality enforcement | scrape relabel (central, but post-emit) | sender or backend | **collector pipeline** — one central, governable point |
| Backpressure | scraper paces itself | any app can flood the backend | collector buffers, batches, applies limits |
| Backend coupling | apps coupled to Prometheus model | apps coupled to backend protocol | apps speak OTLP only; backend swappable |
| Spatial pre-aggregation | not possible at scrape | not possible | **collector sums across local pods** |

### Why the collector-in-the-middle wins for fleets

The OTel Collector as a **per-node DaemonSet or per-cluster gateway** is the modern fleet standard because it converts a hard multi-party problem into a single governable choke point:

- **One place to enforce cardinality** (the collector's `transform`/`filter`/`attributes` processors) across every language and service — you don't have to trust forty SDKs configured by forty teams.
- **One place to do spatial aggregation** (drop `pod`, sum across local pods) — impossible with direct scrape or direct push.
- **One place to handle temporality** (`delta-to-cumulative` processor) — apps emit delta (cheap, FaaS-friendly), the collector converts to cumulative for Prometheus, so the *app* never has to know the backend's model.
- **Decouples app transport from backend protocol** — apps speak only OTLP; you swap Mimir for Datadog by reconfiguring the collector, redeploying *nothing* in the apps.

The emit-side consequence — and the part this page owns — is that **the app's job shrinks to "emit clean OTLP to localhost."** No service discovery, no backend protocol, no scrape endpoint to secure on every pod. That simplicity *is* the fleet win, and it's a deliberate emit-side design choice: standardize every service on OTLP-to-local-collector, and the entire control plane moves to one configurable component.

### The cases where you still emit pull directly

- **Infra exporters** (node-exporter, kube-state-metrics, database exporters) are pull-native and stay that way — they're not your app code.
- **A small, stable, long-lived fleet** where the operational simplicity of "Prometheus scrapes everything" outweighs the collector's flexibility — don't add a collector tier you don't need.
- **The free-liveness property matters more than flexibility** for a critical service — direct scrape gives unambiguous `up==0` without modeling heartbeats. (You can also get this by scraping the collector and emitting per-app heartbeats.)

---

## Multi-Language Fleet Instrumentation Standards

This is the work that most defines the professional tier: making forty services in five languages emit **one coherent signal**. The enemy is *drift* — the Go service calls it `http_request_duration_seconds`, the Java service `http.server.requests`, the Python one `request_latency`, all in different units, with different attributes, so no single dashboard query spans them. The fix is a **fleet instrumentation standard**, enforced in shared code, not prose.

### The standard has five pillars

| Pillar | The rule | Enforced by |
|--------|----------|-------------|
| **Naming** | OTel semantic conventions verbatim (`http.server.request.duration`), no bespoke names where a semconv exists | A shared `initMetrics()` lib + CI lint on metric names |
| **Units** | Always base units: **seconds** (not ms), **bytes** (not KB); declared in the instrument | Instrument construction in the shared lib; lint rejects `_ms`/`_kb` |
| **Attributes** | A fleet allow-list per instrument; semconv attribute keys (`http.request.method`, not `verb`) | SDK View `AllowAttributeKeys`; the lib provides pre-built views |
| **Temporality** | One fleet choice (cumulative *or* delta), set explicitly per backend | The shared exporter constructor in the lib |
| **Resource** | `service.name`, `service.version`, `service.namespace`, `deployment.environment` — bounded, from env, identically | A shared resource-builder in the lib |

### The mechanism: a shared instrumentation library per language, one config source

You do *not* enforce a fleet standard by writing a wiki page and hoping. You write **a thin instrumentation library in each language** — `acme-otel-go`, `acme-otel-java`, `acme-otel-py`, … — that:

1. Constructs the `MeterProvider` with the fleet-standard Views, temporality, Resource, and exemplar filter — so every service that imports it is correct *by default*.
2. Exposes the *blessed* instruments (the standard HTTP/DB/queue metrics) pre-built, so teams use them instead of rolling their own names.
3. Reads its config (interval, endpoint, sampling) from one source of truth (env vars set by the platform), so behavior is consistent across the fleet.

The five SDKs differ in ergonomics, so the *library* absorbs the differences and presents one interface — that's its whole reason to exist. A Go team and a Java team both call `acmeotel.Init("checkout")` and get identical naming, units, attributes, temporality, and exemplars, despite the SDKs underneath being quite different. **The standard is a library, not a document.**

### Semantic conventions are the shared vocabulary — adopt them, don't invent

OTel's semantic conventions (`http.*`, `db.*`, `messaging.*`, `rpc.*`) exist precisely so that a query written against one service works against all of them and against vendor dashboards. The professional move is **adopt semconv verbatim and resist the urge to invent local names.** When you invent `request_latency`, you've forked from every OTel-aware tool, dashboard, and engineer's expectation. When a semconv name *changes* (they do, across versions — `http.method` → `http.request.method`), you absorb the migration *in the shared library's Views*, once, instead of in forty codebases.

### CI as the enforcement backstop

Even with a shared library, someone will hand-roll a metric. A CI check on the exposition (scrape the service in CI, lint the output) catches:

- Names not in semconv and not on the approved bespoke list.
- Non-base units (`_milliseconds`, `_bytes` where base should be seconds/bytes — wait, bytes is base; `_kb`/`_mb` are the violations).
- Unbounded-looking attributes (a high distinct-count attribute on a hot instrument in a staging soak).
- Missing exemplar config on latency histograms.

The lint is the backstop for the library: the library makes the right thing easy, the lint makes the wrong thing *fail the build*.

---

## Code Examples

### Go — the fleet `initMetrics`: Views, exemplars, temporality, cardinality limits

```go
package acmeotel

import (
	"context"
	"time"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/exporters/otlp/otlpmetric/otlpmetricgrpc"
	"go.opentelemetry.io/otel/sdk/metric"
	"go.opentelemetry.io/otel/sdk/metric/metricdata"
	"go.opentelemetry.io/otel/sdk/resource"
	semconv "go.opentelemetry.io/otel/semconv/v1.26.0"
)

// Init builds the fleet-standard MeterProvider. EVERY service calls this.
// One function = one coherent emission contract across the whole Go fleet.
func Init(ctx context.Context, serviceName, version, env, collectorAddr string) (*metric.MeterProvider, error) {
	// Bounded Resource only: service identity, NOT pod/instance (those churn → cardinality bomb).
	res, err := resource.New(ctx,
		resource.WithAttributes(
			semconv.ServiceName(serviceName),
			semconv.ServiceVersion(version),
			semconv.DeploymentEnvironment(env),
		),
	)
	if err != nil {
		return nil, err
	}

	// OTLP push to the LOCAL collector. App knows only localhost; backend is the collector's problem.
	exp, err := otlpmetricgrpc.New(ctx,
		otlpmetricgrpc.WithEndpoint(collectorAddr), // e.g. "localhost:4317"
		// Fleet temporality decision, explicit — never rely on the SDK default.
		// Cumulative here because the backend is Mimir (Prometheus-model).
		otlpmetricgrpc.WithTemporalitySelector(func(metric.InstrumentKind) metricdata.Temporality {
			return metricdata.CumulativeTemporality
		}),
	)
	if err != nil {
		return nil, err
	}

	mp := metric.NewMeterProvider(
		metric.WithResource(res),
		metric.WithReader(metric.NewPeriodicReader(exp,
			metric.WithInterval(15*time.Second), // cost lever: 15s = 4× DPM of 60s. Tuned to the SLO.
		)),

		// VIEW 1: every duration instrument → base-2 exponential histogram.
		// No per-service bucket design, ~1 series each, uniform accuracy, fleet-wide.
		metric.WithView(metric.NewView(
			metric.Instrument{Kind: metric.InstrumentKindHistogram},
			metric.Stream{
				Aggregation: metric.AggregationBase2ExponentialHistogram{MaxSize: 160, MaxScale: 20},
			},
		)),

		// VIEW 2: allow-list attributes on the HTTP histogram. user_id/request_id can't become series.
		metric.WithView(metric.NewView(
			metric.Instrument{Name: "http.server.request.duration"},
			metric.Stream{
				AllowAttributeKeys: attribute.NewSet(
					attribute.String("http.request.method", ""),
					attribute.String("http.route", ""),
					attribute.String("http.response.status_code", ""),
				),
				AggregationCardinalityLimit: 2000, // bomb → otel.metric.overflow, not OOM
			},
		)),
	)
	otel.SetMeterProvider(mp)
	// Exemplar filter defaults to trace_based in the SDK (correct): exemplars only for SAMPLED spans.
	return mp, nil
}
```

The point of this example: **the entire fleet's emission policy is one function.** Naming and units come from the blessed instruments built on top of this; temporality, exemplars, cardinality limits, exponential histograms, and a bounded Resource are all set once, here, and inherited by every service that calls `Init`.

### Go — recording with an exemplar (client_golang, the pull/Prometheus path)

```go
import "github.com/prometheus/client_golang/prometheus"

// When you're on direct-Prometheus (not OTel), use ObserveWithExemplar to attach
// the trace ID so the histogram bucket links to the trace.
func observeWithTrace(h prometheus.ObserverVec, traceID string, route string, d float64) {
	obs := h.WithLabelValues(route)
	if eo, ok := obs.(prometheus.ExemplarObserver); ok && traceID != "" {
		eo.ObserveWithExemplar(d, prometheus.Labels{"trace_id": traceID})
		return
	}
	obs.Observe(d) // fall back if exemplars unsupported
}
```

`ObserveWithExemplar` is the client_golang mechanism; the `trace_id` must come from the active span context (extract it where the span is live), or the exemplar points nowhere.

### Java — Micrometer + OTel bridge: SLO histogram, exemplars, tag cap

```java
import io.micrometer.core.instrument.*;
import io.micrometer.core.instrument.config.MeterFilter;
import io.micrometer.registry.otlp.OtlpConfig;
import io.micrometer.registry.otlp.OtlpMeterRegistry;
import java.time.Duration;
import java.util.Map;

public final class AcmeMetrics {

    /** Fleet-standard registry. Micrometer → OTLP → local collector. */
    public static MeterRegistry init(String serviceName, String version, String env) {
        OtlpConfig cfg = new OtlpConfig() {
            @Override public String get(String key) { return null; }
            @Override public String url() { return "http://localhost:4318/v1/metrics"; }
            @Override public Duration step() { return Duration.ofSeconds(15); } // export interval / DPM lever
            @Override public io.micrometer.registry.otlp.AggregationTemporality aggregationTemporality() {
                // Explicit fleet choice — cumulative for the Mimir backend.
                return io.micrometer.registry.otlp.AggregationTemporality.CUMULATIVE;
            }
            @Override public Map<String, String> resourceAttributes() {
                return Map.of("service.name", serviceName, "service.version", version,
                              "deployment.environment", env);
            }
        };
        MeterRegistry registry = new OtlpMeterRegistry(cfg, io.micrometer.core.instrument.Clock.SYSTEM);

        // Cardinality cap as code (defense line 2): excess 'uri' values → denied, not OOM.
        registry.config().meterFilter(
            MeterFilter.maximumAllowableTags("http.server.requests", "uri", 100, MeterFilter.deny()));
        // Exemplars: Micrometer attaches the active span's trace ID when a Tracer is present
        // (micrometer-tracing bridge), so percentile-histogram buckets link to traces.
        return registry;
    }

    public static Timer httpTimer(MeterRegistry r) {
        return Timer.builder("http.server.request.duration")  // semconv name
            .publishPercentileHistogram()                     // AGGREGATABLE buckets, not client quantiles
            .serviceLevelObjectives(                          // exact bucket edges at SLO thresholds
                Duration.ofMillis(50), Duration.ofMillis(300), Duration.ofSeconds(2))
            .register(r);
    }
}
```

The Micrometer-specific trap restated for fleet context: `publishPercentiles()` emits **client-side, non-aggregatable** quantiles (the summary trap); `publishPercentileHistogram()` emits **aggregatable buckets**. In a fleet, the latter is mandatory — a per-pod quantile can't be merged into a fleet quantile. The `micrometer-tracing` bridge is what makes exemplars flow.

### Python — OTel SDK: views, exemplar filter, delta for a Lambda

```python
from opentelemetry.sdk.metrics import MeterProvider, Counter, Histogram
from opentelemetry.sdk.metrics.export import (
    PeriodicExportingMetricReader,
    AggregationTemporality,
)
from opentelemetry.sdk.metrics.view import View, ExplicitBucketHistogramAggregation
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter

def init_metrics(service: str, version: str, env: str, collector: str) -> MeterProvider:
    resource = Resource.create({
        "service.name": service,
        "service.version": version,
        "deployment.environment": env,
        # No pod/instance here — bounded Resource only.
    })

    # DELTA temporality: this process is an AWS Lambda. Each invocation is a fresh
    # zero-start process; cumulative counters would be meaningless across invocations.
    exporter = OTLPMetricExporter(
        endpoint=collector,
        preferred_temporality={
            Counter: AggregationTemporality.DELTA,
            Histogram: AggregationTemporality.DELTA,
        },
    )
    reader = PeriodicExportingMetricReader(exporter, export_interval_millis=10_000)

    # View: force exponential-ish bucketing and drop unbounded attrs on the hot instrument.
    duration_view = View(
        instrument_name="http.server.request.duration",
        attribute_keys={"http.request.method", "http.route", "http.response.status_code"},
        aggregation=ExplicitBucketHistogramAggregation(
            boundaries=[0.005, 0.01, 0.025, 0.05, 0.1, 0.3, 0.5, 1.0, 2.0]
        ),
    )

    provider = MeterProvider(resource=resource, metric_readers=[reader], views=[duration_view])
    # Exemplar filter is trace_based by default in the SDK; set OTEL_METRICS_EXEMPLAR_FILTER
    # to override. trace_based is the fleet default.
    return provider
```

`attribute_keys` on the `View` is Python's allow-list — anything not listed is dropped before export. The delta temporality is the load-bearing fleet decision for a serverless deployment: get it wrong and the Lambda's counters are garbage.

### Rust — `opentelemetry` SDK: views, exponential histograms, bounded resource

```rust
use opentelemetry::KeyValue;
use opentelemetry_otlp::WithExportConfig;
use opentelemetry_sdk::{
    metrics::{Aggregation, Instrument, SdkMeterProvider, Stream, Temporality},
    Resource,
};
use std::time::Duration;

fn init_metrics(service: &str, version: &str, env: &str) -> SdkMeterProvider {
    let resource = Resource::new(vec![
        KeyValue::new("service.name", service.to_string()),
        KeyValue::new("service.version", version.to_string()),
        KeyValue::new("deployment.environment", env.to_string()),
        // bounded resource — no pod/instance identity
    ]);

    let exporter = opentelemetry_otlp::new_exporter()
        .tonic()
        .with_endpoint("http://localhost:4317")
        // Explicit fleet temporality: cumulative for a long-lived Prometheus-backed service.
        .build_metrics_exporter(Box::new(Temporality::Cumulative))
        .expect("otlp metric exporter");

    // View: every histogram → exponential. No hand bucket design across the fleet.
    let exp_hist = |i: &Instrument| {
        if i.name.ends_with(".duration") {
            Some(
                Stream::new()
                    .name(i.name.clone())
                    .aggregation(Aggregation::Base2ExponentialHistogram {
                        max_size: 160,
                        max_scale: 20,
                        record_min_max: true,
                    })
                    // allow-list attributes on the hot instrument
                    .allowed_attribute_keys(vec![
                        "http.request.method".into(),
                        "http.route".into(),
                        "http.response.status_code".into(),
                    ]),
            )
        } else {
            None
        }
    };

    SdkMeterProvider::builder()
        .with_resource(resource)
        .with_periodic_exporter(exporter) // interval configured on the reader builder in full code
        .with_view(exp_hist)
        .build()
}
```

The Rust SDK expresses Views as closures matching instruments to `Stream`s — the same control plane (rename, aggregation, attribute allow-list) as Go/Python, just in idiomatic Rust. `Temporality::Cumulative` is the explicit fleet choice.

### Node — OTel SDK with exemplars + prom-client interop

```js
const { MeterProvider, PeriodicExportingMetricReader,
        ExplicitBucketHistogramAggregation, View } = require("@opentelemetry/sdk-metrics");
const { OTLPMetricExporter } = require("@opentelemetry/exporter-metrics-otlp-grpc");
const { Resource } = require("@opentelemetry/resources");
const { AggregationTemporality } = require("@opentelemetry/sdk-metrics");

function initMetrics(service, version, env) {
  const resource = new Resource({
    "service.name": service,
    "service.version": version,
    "deployment.environment": env, // bounded resource only
  });

  const exporter = new OTLPMetricExporter({
    url: "http://localhost:4317",
    // Explicit fleet temporality. Cumulative for the Prometheus-model backend.
    temporalityPreference: AggregationTemporality.CUMULATIVE,
  });

  const provider = new MeterProvider({
    resource,
    readers: [new PeriodicExportingMetricReader({
      exporter,
      exportIntervalMillis: 15000, // DPM cost lever
    })],
    views: [
      // Allow-list attributes + explicit SLO-aligned buckets on the hot instrument.
      new View({
        instrumentName: "http.server.request.duration",
        attributeKeys: ["http.request.method", "http.route", "http.response.status_code"],
        aggregation: new ExplicitBucketHistogramAggregation(
          [0.005, 0.01, 0.025, 0.05, 0.1, 0.3, 0.5, 1, 2], true /* recordMinMax */),
      }),
    ],
  });
  // Exemplar filter: set OTEL_METRICS_EXEMPLAR_FILTER=trace_based (the fleet default).
  return provider;
}
module.exports = { initMetrics };
```

`attributeKeys` is Node's View allow-list. Note the same five decisions appear in *every* language's `initMetrics` — naming, units (seconds), allow-listed attributes, explicit temporality, bounded Resource — which is exactly the point: the **fleet standard is the same shape in five SDKs**, absorbed by a shared library so teams never assemble this by hand.

---

## Worked Example — Designing a Fleet Metrics Contract

You inherit a fleet: 38 services, Go/Java/Python/Node, three teams, two backends (a Mimir cluster and a Datadog account a different team uses), and a dashboard graveyard where the same query never works across two services. The CTO wants "one observability story." Here is the emit-side design, end to end.

**Step 1 — pick the spine: semantic conventions + OTLP.** Mandate OTel semconv names verbatim and OTLP as the *only* app-side transport. Every app emits OTLP to a local collector; the collector fans out (remote-write to Mimir, OTLP to Datadog). Apps never know there are two backends. This single decision kills the naming drift and the backend-coupling problem at once.

**Step 2 — write the temporality rule.** Mimir wants cumulative; Datadog prefers delta. Rather than make each app choose, **apps emit cumulative** (simpler, reset-resilient) and the **collector's `delta`/`cumulative-to-delta` processor** produces delta for the Datadog branch. One rule: *apps are cumulative.* The translation is a pipeline concern, off the app's plate.

**Step 3 — build the five shared libraries.** `acme-otel-{go,java,py,node}` (Rust later), each exposing `Init(service, version, env)` that wires: bounded Resource, exponential histograms via View, allow-listed attributes on the blessed HTTP/DB/queue instruments, `trace_based` exemplars, 15s interval, cumulative temporality. A team adopts the standard by deleting their hand-rolled setup and calling `Init`. **The standard ships as a dependency bump.**

**Step 4 — define the blessed instrument catalog.** A short list every service uses verbatim:

| Concept | Instrument | Type | Unit | Attributes (allow-listed) |
|---------|------------|------|------|---------------------------|
| HTTP server latency | `http.server.request.duration` | exp. histogram | s | method, route, status_code |
| HTTP server count | (from histogram `_count`) | — | — | (don't double-emit) |
| DB call latency | `db.client.operation.duration` | exp. histogram | s | db.system, db.operation |
| Queue lag | `messaging.process.duration` | exp. histogram | s | messaging.system, destination |
| In-flight requests | `http.server.active_requests` | UpDownCounter | {request} | method, route |
| Errors | (from `status_code`/`error.type` on the above) | — | — | — |

The catalog is deliberately tiny — semantic conventions, no bespoke names, nothing derivable double-emitted. This is the senior "what not to measure" discipline scaled to "what the *whole fleet* is allowed to measure by default."

**Step 5 — allocate the cardinality budget.** Mimir comfortably holds ~8M active series; reserve 30%; allocate the rest by tier (Tier-1 APIs 200k each, workers 5k each). Encode each cap as an `AggregationCardinalityLimit` in the team's `Init` config. Alert on 80% of fleet budget, 80% of any cap, and any `otel.metric.overflow` point.

**Step 6 — wire exemplars + the CI lint.** `trace_based` exemplars on by default (from the shared lib) + scrape/collector configured for OpenMetrics so they flow to Grafana with trace click-through. A CI job scrapes each service in a smoke test and fails the build on: non-semconv names, non-base units, an attribute with >50 distinct values in the soak, or a latency histogram without exemplars.

**Step 7 — migrate incrementally with Views.** The 38 services don't convert in a day. Legacy `request_time_ms` (milliseconds, wrong name) gets a **View rename + unit conversion** in the shared lib, so the dashboard reads `http.server.request.duration` in seconds *before* the team refactors the call sites. The standard rolls out faster than the code changes.

**The outcome:** one dashboard query (`histogram_quantile(0.99, sum by (le, service_name)(rate(http_server_request_duration_seconds_bucket[5m])))`) works across all 38 services because they emit the *same instrument, name, unit, attributes, and temporality*. Cardinality is capped in each SDK. Exemplars link every latency spike to a trace. The bill is allocated and alerted. **That coherence is the deliverable — and every piece of it was an emit-side decision, made once, in shared code.**

---

## A Real Cardinality Incident, Walked Through

A walk-through in the register of the [debugging professional](../01-debugging/professional.md#a-worked-incident-timeline) timeline, because cardinality blowups *are* incidents at fleet scale.

**Symptom (14:40 UTC):** Mimir's ingesters start OOM-restarting. Write path latency climbs; some remote-writes are rejected with `per-user series limit exceeded`. The on-call SRE pages. Active series on the cluster jumped from 6.2M to 9.8M in 25 minutes and is still climbing.

**Step 1 — find *which metric*.** Query the TSDB's own metrics: `topk(10, count by (__name__)({__name__=~".+"}))`. One name dominates: `payment_attempt_duration_seconds_bucket` — 3.1M series, up from ~40k an hour ago.

**Step 2 — find *which label* exploded.** `count(count by (card_bin) (payment_attempt_duration_seconds_bucket))` → 41,000 distinct `card_bin` values. Someone added the card BIN (first 6–8 digits of the card number) as a *metric attribute*. BINs are effectively unbounded across a payment fleet. **The bomb: an unbounded attribute on a hot histogram (× 12 buckets × pods).**

**Step 3 — confirm the source.** `count by (service_name)(payment_attempt_duration_seconds_bucket{...})` points at `payments-api`. The deploy bot shows `payments-api v4.12` shipped at 14:12 — a "let's see fraud rates by BIN" change. The author thought a metric attribute was the place for it.

**Step 4 — mitigate (stop the bleeding).** Two mitigations, in order:
1. **Collector drop rule** (fastest, no app deploy): a `transform` processor in the collector deletes the `card_bin` attribute from that instrument. Series stop being minted within one scrape interval. *This is the win of the collector-in-the-middle topology — one config change, fleet-wide, no app redeploy.*
2. Backend per-user limit already rejected the worst of it (that's why writes failed — the limit did its job as the last-resort ceiling).

**Step 5 — why the SDK didn't catch it.** Post-incident: `payments-api` predated the shared `acme-otel-go` library and hand-rolled its `MeterProvider` *without* the allow-list View or the cardinality limit. Had it used `Init`, the `card_bin` attribute would have been **dropped by `AllowAttributeKeys`** before export — the bomb would never have left the process. The wiki said "don't add unbounded attributes"; the wiki enforced nothing.

**Step 6 — the real fix (root causes, plural).**
- The BIN dimension is an **analytics question, not a metric** — it belongs in the warehouse / wide events, not a series. (Senior "per-row business event → not a metric.")
- `payments-api` is migrated onto the shared library so the allow-list View enforces attribute bounds *in the SDK*.
- CI lint gains a soak-test check that fails the build when any attribute exceeds 1,000 distinct values in staging — so the next BIN dies in CI, not in prod.
- A churn alert (`rate(...head_series_created_total[1h])`) is added; it would have fired *before* the OOM, when series were being minted, not after.

**Lessons:**
1. **The cheapest place to stop a cardinality bomb is the SDK allow-list View** — in the app's own repo, before export. The collector drop rule saved the day, but only because the SDK *failed* to.
2. **An unbounded attribute is the same bug whether it's a label (senior) or an OTel attribute (professional).** The fix is structural: allow-list, fail closed.
3. **The collector-in-the-middle topology turned a "redeploy 1 service under fire" problem into a "one config change" mitigation.** That's the fleet-scale payoff of centralizing the control plane.
4. **The backend limit worked as designed** — it rejected writes (data loss) as the *last* resort, which is exactly its job. You never want to rely on it, but you're glad it's there.

---

## Coding Patterns

### Pattern 1 — One `Init` per language, the whole contract in it

```go
mp, _ := acmeotel.Init(ctx, "checkout", version, env, "localhost:4317")
// Views, temporality, exemplars, bounded Resource, cardinality limits — all inside Init.
```

### Pattern 2 — Allow-list attributes in a View (fail closed)

```go
metric.Stream{ AllowAttributeKeys: attribute.NewSet(/* only the bounded keys */) }
// Anything not listed is dropped before export. The next engineer's user_id can't leak.
```

### Pattern 3 — Cardinality limit turns OOM into a signal

```go
metric.Stream{ AggregationCardinalityLimit: 2000 } // overflow → otel.metric.overflow; alert on it
```

### Pattern 4 — Exemplar recorded inside the span scope

```go
// span MUST be active in ctx here, or the exemplar has no trace ID.
hist.Record(ctx, d.Seconds(), metric.WithAttributes(attrs...))
```

### Pattern 5 — Temporality matched to lifetime, explicitly

```text
long-lived + Prometheus backend → cumulative (set on the exporter, never defaulted)
serverless / FaaS               → delta
Datadog branch                  → app stays cumulative; collector converts to delta
```

### Pattern 6 — Bounded Resource, pod identity out of metrics

```go
resource.WithAttributes(semconv.ServiceName(svc), semconv.ServiceVersion(ver), semconv.DeploymentEnvironment(env))
// NO pod.name / instance.id — those multiply every series and churn on every roll.
```

### Pattern 7 — Migrate via View, not via coordinated deploy

```go
// Legacy name/unit fixed in the SHARED LIB's View; call sites untouched until convenient.
metric.NewView(
    metric.Instrument{Name: "request_time_ms"},
    metric.Stream{Name: "http.server.request.duration"}, // rename; unit handled by re-bucketing
)
```

---

## Clean Code

- **There is exactly one `Init`/`initMetrics` per language**, in a shared library, and every service calls it. No hand-rolled `MeterProvider` in a service repo.
- **Every metric name is an OTel semantic convention** or on a short, reviewed bespoke allow-list. No `request_latency` where `http.server.request.duration` exists.
- **Every unit is a base unit** — seconds, bytes — declared on the instrument. No `_ms`, no `_kb`.
- **Every hot instrument has an allow-list View** (`AllowAttributeKeys`), so cardinality fails closed.
- **Every instrument has a cardinality limit**, and overflow is alerted on.
- **Temporality is set explicitly on the exporter**, never inherited from the SDK default, and is uniform across the fleet (per backend).
- **Exemplars are on (`trace_based`) for every latency histogram**, and metric records happen inside the active span scope.
- **The Resource is bounded** — service identity only, no pod/instance/node.
- **Duration instruments are exponential histograms** via a single fleet View, not per-service hand-designed buckets.
- **A CI lint scrapes the service and fails the build** on naming, unit, cardinality, and missing-exemplar violations.

---

## Best Practices

1. **Make the contract a library, not a wiki.** A shared `Init` per language that's correct by default beats any document. Drift dies when the right thing is the easy thing.
2. **Adopt OTel semantic conventions verbatim.** Resist inventing local names; absorb semconv version changes in the shared lib's Views, once.
3. **Enforce cardinality in the SDK with allow-list Views + limits.** It's the most reliable control still in your repo, acting before export. The collector and backend are backstops, not the plan.
4. **Set temporality explicitly and uniformly.** Never trust the SDK default (it differs by language). Cumulative for long-lived + Prometheus; delta for serverless; convert at the collector for mixed backends.
5. **Turn exemplars on for every latency histogram** (`trace_based`), and record metrics inside the span scope. It's the highest-leverage, lowest-cost emit-side win.
6. **Prefer exponential/native histograms fleet-wide** via one View. No bucket design, ~order-of-magnitude fewer series, uniform accuracy.
7. **Keep the Resource bounded** and push pod/instance identity out of metrics. Resource attributes multiply *every* series.
8. **Price every new metric in the backend's billing unit** before it ships — active series, DPM, or custom-metric count. A hot unbounded attribute is a five-figure line item.
9. **Aggregate at the source** — drop un-queried dimensions, sum pod away at the collector — but never collapse a load-bearing (SLO/alert/failure-mode) dimension.
10. **Centralize on OTLP → local collector** so cardinality, temporality, aggregation, and backend choice all live in one governable component, and apps stay simple.

---

## Edge Cases & Pitfalls

- **SDK temporality default differs by language.** Java/Go/Python don't agree out of the box; the Prometheus exporter forces cumulative regardless. Always set it explicitly, or the same metric resets differently across services.
- **Exemplar with no trace context.** Recording a metric outside the active span scope (background flusher, after `span.End()`, an unpropagated goroutine) yields an exemplar with no trace ID — useless. Record inside the span.
- **`always_on` exemplar filter pointing at unsampled traces.** With trace sampling < 100%, `always_on` produces exemplars whose trace IDs aren't stored — click leads to "trace not found." Use `trace_based` unless you tail-sample or sample at 100%.
- **Resource attribute churn.** `pod.name`/`instance.id` in the Resource re-mints every series on every deploy/scale. Active series can look flat while the index balloons. Keep the Resource bounded.
- **OpenMetrics negotiation off → exemplars silently dropped.** The client emits exemplars; the scrape drops them if it doesn't send the OpenMetrics `Accept` header / `--enable-feature=exemplar-storage`. Like native histograms, every link must support them.
- **Delta export drop = permanent loss.** A serverless function on delta temporality that fails to flush before freeze/exit loses that invocation's increments forever. Flush explicitly before the runtime suspends.
- **Cardinality limit hides the real attribute set.** Once an instrument overflows to `otel.metric.overflow`, you've lost the ability to distinguish the legitimate series above the cap. Set the limit *above* the real working set, and alert on overflow so you raise it deliberately.
- **Collector as a single point of failure.** Centralizing on a local collector means its outage stops *all* metrics from that node. Run it as a DaemonSet with resource limits and its own liveness; don't let it become an unmonitored chokepoint.
- **`UpDownCounter` vs `Gauge` summed wrong.** Summing gauges (absolute values) across instances is usually meaningless; summing up-down counters (deltas you maintained) is meaningful. Picking the wrong one makes fleet-aggregate dashboards lie.
- **Async callback doing real work.** An `ObservableGauge` callback that queries a DB runs on every collection cycle — a self-synchronized load spike. Keep callbacks reading cached/in-memory values only.

---

## Common Mistakes

1. **Hand-rolling the `MeterProvider` in a service** instead of using the shared `Init`, reintroducing naming/unit/temporality drift and skipping the cardinality Views.
2. **Inventing metric names** where a semantic convention exists, forking from every OTel-aware tool and dashboard.
3. **Putting an unbounded attribute on a hot instrument** (`card_bin`, `user_id`, raw path) — the classic fleet cardinality bomb.
4. **Baking `pod`/`version` into series identity** and budgeting active series but not churn, so the index balloons on every deploy.
5. **Relying on the SDK's default temporality**, which differs by language, so resets are inconsistent fleet-wide.
6. **Cumulative counters on a Lambda** — each invocation is a fresh zero-start process; the running total is meaningless.
7. **`publishPercentiles()` (Micrometer) or summary-style quantiles** in a multi-replica service — non-aggregatable per-pod quantiles that can't be merged into a fleet quantile.
8. **Recording metrics outside the span scope** and getting exemplars with no trace ID.
9. **Pricing metrics in "series count" on a DPM- or custom-metric-billed backend**, optimizing the wrong cost dimension.
10. **Treating the collector / backend limit as the cardinality plan** instead of a backstop, so the SDK never catches the bomb and the limit's data-loss is the first signal.

---

## Tricky Points

- **The View is configured once at provider construction but applies to every instrument** — it's a *process-wide* policy, which is exactly why the fleet standard is a provider-construction standard, not a per-instrument convention.
- **An allow-list (`AllowAttributeKeys`) fails closed; a deny-list fails open.** Only the allow-list is safe at fleet scale, because the next unbounded attribute is one you haven't thought to deny yet.
- **Exemplars are sampled, not exhaustive** — the reservoir keeps a small fixed number per bucket per collection. You get *a* slow trace, not *every* slow trace. That's enough to debug, but don't expect completeness.
- **Cumulative survives a dropped export; delta does not.** With cumulative the next export carries the running total and recovers; with delta the increment is simply gone. This trade-off drives delta deployments toward short intervals + reliable transport.
- **Native/exponential histograms are aggregatable *and* high-resolution** — not a compromise. The only cost is end-to-end ecosystem support. Where supported, they beat classic histograms on series count *and* accuracy.
- **Resource attributes multiply every series**; a single unbounded Resource attribute is worse than an unbounded instrument attribute, because it hits *all* of the process's metrics, not one.
- **The collector-in-the-middle moves the control plane out of the app**, which is the fleet win — but it also means cardinality enforcement *can* happen post-emit, which tempts teams to skip the SDK Views. Don't: the SDK is cheaper and in your repo.
- **"Aggregate at the source" and "keep the SLO dimension" are in tension.** Drop the un-queried dimensions; never drop the one an alert or SLO reads. The judgment is which dimension is load-bearing.

---

## Anti-Patterns at Professional Level

1. **The wiki-as-enforcement.** "We have a metrics naming guide." Nobody reads it; drift wins. The standard must be executable code (a library) and a CI gate, not prose.
2. **The snowflake `MeterProvider`.** Every service assembling its own SDK config "because our case is special." There are almost no special cases; there is a shared `Init` they should be using.
3. **Cardinality-by-collector-only.** Trusting the collector/backend to catch every bomb, so the SDK has no allow-list. The bomb's data-loss at the backend limit becomes the first signal — at 3 a.m.
4. **Exemplars-off because "we'll add them later."** You won't. Exemplars go in the shared `Init` default or they never go in, and you keep paying the metric→trace correlation tax forever.
5. **The vanity async gauge.** An `ObservableGauge` callback hitting a database every collection cycle, turning your scrape interval into a synchronized load spike. Async callbacks read memory only.
6. **Pricing in the wrong unit.** Optimizing series count for a Datadog (custom-metric-billed) fleet, or DPM for a series-billed one. Know the billing unit; design to it.
7. **Per-language drift accepted as inevitable.** "Go does it this way, Java does it that way." The shared library exists precisely to absorb SDK differences and present one contract.
8. **The metric that's really an event.** `payment_attempt{card_bin=...}` — an analytics question forced into a series. It belongs in the warehouse/wide events, not the TSDB.
9. **Temporality by default.** Never explicitly choosing, so a backend migration or a language mix silently changes reset semantics.
10. **The unmonitored collector chokepoint.** Centralizing on a local collector and then not monitoring *it* — so its outage drops all metrics silently, and you find out from the absence of dashboards.

---

## Apply it

1. Define the user or business outcome that **Metrics — Professional (Staff / Principal) Level** should improve.
2. Assign one owner for code, contracts, operations, and incidents.
3. Split delivery into reversible increments that produce evidence early.
4. Publish responsibilities, escalation paths, and compatibility windows.
5. Stop or expand only when the agreed measures support that decision.

## Verify your work

- Each increment has an owner, rollback path, and observable exit condition.
- Adoption, reliability, delivery time, and coordination cost are measured.
- Incident and migration exercises prove that responsibility is executable.
- The old path is removed only after telemetry proves it is unused.

## Review questions

- Which measurable outcome justifies investing in Metrics — Professional (Staff / Principal) Level?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
