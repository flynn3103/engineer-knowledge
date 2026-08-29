# Telemetry Cost & Sampling Strategy — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Telemetry Cost & Sampling Strategy** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Topic:** [Telemetry Cost & Sampling Strategy Roadmap](README.md)
> **Focus:** The OTel Collector as the single control point. Tail-sampling policies you can paste into production, the cardinality math behind a bill, and why tail sampling forces every span of a trace onto the same collector.

---

## Core Concepts

### 1. The Collector is where cost decisions live — by config, not by deploy

The application should emit telemetry generously and *know nothing* about sampling. Every cost decision — which traces to keep, which labels to strip, which spans to drop — belongs in the Collector's pipeline, changeable with a config reload. This decoupling is what lets you respond to a runaway bill in minutes instead of a release cycle.

### 2. Processor order is semantics, not style

A Collector pipeline is an ordered list. `memory_limiter` must come *first* (it protects everything after it). `tail_sampling` must come *before* `batch` (you sample, then batch the survivors). An `attributes` processor that drops a label must run *before* the data is counted into a metric you derive alerts from. Reordering processors changes behaviour, sometimes silently.

### 3. Cardinality is a product; you must do the multiplication

Every metric's series count is the product of its labels' distinct values, times the metric's internal series (a histogram is ~14 series before labels). One label with a million values doesn't add a million — it *multiplies*. The only defence is to compute the product *before* shipping the label, and to allow-list anything user-supplied.

### 4. Tail sampling needs the whole trace in one place

A tail decision ("this trace errored, keep it") requires *seeing every span of the trace*. If spans of one `trace_id` land on different Collector instances, no instance has the whole trace and the decision is wrong. This single constraint forces the **agent → gateway** topology in any non-trivial deployment.

### 5. Cost control is mostly *moving* and *aggregating*, not deleting

The cheapest data is the summary you kept instead of the raw stream you dropped. The cheapest label is the one you moved from a metric (expensive cardinality) to a trace attribute (cheap). Aggregate at the source, move identity to where it's cheap, and keep exemplars as the bridge back — you lose far less than you save.

---

## Cost Drivers per Signal

The junior table named the drivers. Here is the arithmetic behind each one.

### Metrics — cardinality math

A histogram is not one series. It is one series per bucket, plus `_sum` and `_count`:

```text
http_request_duration_seconds (Prometheus default ~10 buckets + _sum + _count) ≈ 14 series
   labels: method(4) × status(6) × route(20)
   = 14 × 4 × 6 × 20 = 6,720 series          ← healthy
```

Every label *multiplies*. The killer is an identity label:

```text
   + user_id (500,000 values)
   = 6,720 × 500,000 = 3,360,000,000 series  ← 3.36 BILLION; TSDB dead
```

The label call cost nothing at write time. The cardinality it created is the entire bill — and it lands on *every* tenant sharing that TSDB.

### Logs — volume math

Logs cost bytes × retention, with an index multiplier:

```text
   2,000 log lines/sec × 1.2 KB/line = 2.4 MB/sec
   = ~207 GB/day raw
   × 30 days retention = ~6.2 TB stored at any time
   × (often 2–5× for the search index) = the real bill
```

Turning DEBUG on doubles line count; adding three fat fields per line doubles bytes. Both compound against retention.

### Traces — volume × spans math

```text
   50,000 req/sec × 30 spans/trace = 1,500,000 spans/sec
   × ~1 KB/span = 1.5 GB/sec ingested
   = ~129 TB/day at 100% sampling   ← unaffordable; this is why traces are sampled
```

Keep 1% and that's ~1.3 TB/day — still large, which is why tail sampling (keep the *useful* 1.8%, not a blind 1%) matters.

### Wide events / high dimensionality

A "wide event" replaces dozens of low-cardinality metrics with one very high-dimensionality record per request (hundreds of fields, including high-cardinality ones like `user_id`, `build_sha`, `feature_flag`). It dodges the metrics cardinality cliff by *not pre-aggregating* — you aggregate at query time instead. The cost moves from "series stored forever" to "events ingested and queried." This is the Honeycomb model; metrics carry the cheap aggregate, wide events carry the high-dimensionality detail.

---

## Cardinality Control

You control cardinality in three escalating ways, cheapest first.

**1. Don't emit the label.** The only label with zero cost is the one you never added. Treat every new label as a cardinality decision, made on purpose, with the product computed.

**2. Allow-list the values.** When a label comes from user input or an external system, map it through a fixed allow-list; anything unknown collapses to `"other"`. This caps an unbounded source at the instrumentation site (covered in [Metrics — Middle](../04-metrics/middle.md)).

**3. Drop or rewrite at the Collector.** When the bomb already shipped, strip it in the `attributes` processor before it reaches the backend. This is the emergency lever — config push, no deploy.

The deeper move is **move identity off the metric entirely.** A metric should carry the *category* (`tier="enterprise"`); the *identity* (`customer_id="cus_8X2k"`) belongs on a trace attribute, a log field, or an exemplar — all places where high cardinality is cheap because they aren't pre-aggregated into permanent series.

### Worked cardinality-explosion example — with numbers and the fix

A team adds a checkout latency histogram. To debug one merchant's slow checkouts, someone adds `merchant_id` "temporarily."

```text
metric: checkout_duration_seconds   (~14 series: 12 buckets + _sum + _count)
labels BEFORE:  status_class(4) × region(3)
   = 14 × 4 × 3 = 168 series                      ← fine

labels AFTER adding merchant_id (40,000 merchants):
   = 14 × 4 × 3 × 40,000 = 6,720,000 series       ← 6.72 MILLION for ONE metric
```

Prometheus RAM climbs over two days, OOMs at 02:30, crash-loops replaying its WAL, and **every dashboard on that server goes dark** — including the checkout incident the label was added to debug.

**The Collector fix** — strip the label before it reaches the backend, while keeping `merchant_id` as a cheap *trace* attribute for per-merchant drill-down:

```yaml
processors:
  attributes/strip-merchant-id-from-metrics:
    actions:
      - key: merchant_id
        action: delete          # remove from every metric data point

service:
  pipelines:
    metrics:
      receivers:  [otlp]
      processors: [memory_limiter, attributes/strip-merchant-id-from-metrics, batch]
      exporters:  [prometheusremotewrite]
```

Series for that metric drop back to `14 × 4 × merchant_tier(4) × 3 = 672` if you replace identity with category. Per-merchant debugging moves to traces, where `merchant_id` costs nothing.

---

## Head vs Tail Sampling

You met both at junior level. Here are the two extra ideas a middle engineer needs: **rate-limiting sampling** and **consistent/deterministic** decisions.

> **Scenario.** A checkout service: **50,000 req/sec**, ~30 spans/trace, 0.3% error, 0.5% slow (>2s). You want a small bill and zero lost errors or slow traces.

**Head (probabilistic, 1%).** A weighted coin flip at trace start, before the request runs. Cheap and stateless — but blind. It keeps ~1% of *everything*, so it keeps only ~1% of your errors. Good as a flat volume cap; useless for "keep the interesting ones." The OTel `probabilistic_sampler` makes this *deterministic*: it hashes the `trace_id`, so the same trace yields the same decision in every service — a preview of consistent sampling.

**Rate-limiting sampling.** Instead of a percentage, keep at most *N traces per second* (e.g. `spans_per_second: 500`). This caps cost in absolute terms regardless of traffic spikes — useful when a percentage would still blow the budget during a flash sale. The trade: the effective sample *rate* now varies with traffic, which complicates adjusted-count math.

**Tail.** The Collector buffers all spans of each trace until it completes, then applies policies to the *finished* trace:

```text
  policy 1: status == ERROR   → KEEP 100%   (it saw the error)
  policy 2: duration > 2s      → KEEP 100%   (it saw the latency)
  policy 3: everything else    → KEEP 1%     (representative sample)
```

You now keep every error, every slow trace, and 1% of normal traffic — roughly 1.8% of all traces, but the *right* 1.8%. The price: the Collector holds every in-flight trace in memory for the decision window, and **must see all of a trace's spans** — which constrains topology (next section).

**Consistent / deterministic sampling (preview).** If service A keeps a trace but service B independently drops its half, you get a broken, half-empty trace. The fix is that the keep/drop decision is a *function of the `trace_id`* — same ID, same decision, everywhere. Head sampling gets this for free (hash the ID); tail sampling gets it because one collector decides for the whole trace. Full statistical treatment — and the maths of combining head and tail rates honestly — is in [`senior.md`](senior.md).

| | **Head** | **Tail** |
|---|---|---|
| Decided | at trace start | after trace completes |
| Sees if interesting? | No | Yes |
| Memory | ~zero | buffers every in-flight trace |
| Needs all spans co-located? | No | **Yes** |
| Keeps all errors? | only ~sample_rate | **100%** |
| Best for | uniform cap, huge fleets | keeping the traces that matter |

---

## The OTel Collector as Control Point

The Collector is a pipeline of **processors** between receivers and exporters. The cost-relevant ones:

| Processor | Job | Order note |
|---|---|---|
| **`memory_limiter`** | Sheds load before RAM exhaustion. | **First**, always. Protects everything downstream. |
| **`probabilistic_sampler`** | Keep N% of traces by hashing `trace_id`. | Early, to cut volume cheaply. |
| **`tail_sampling`** | Buffer whole traces, keep by policy. | After receive, before `batch`. Gateway tier only. |
| **`filter`** | Drop spans/metrics/logs matching a predicate. | Drop noise (health checks) early. |
| **`attributes`** | Add/delete/rewrite attributes (e.g. strip a label). | Before the data is exported or counted. |
| **`batch`** | Group telemetry for efficient export. | **Last**, just before exporters. |

### Agent vs gateway topology — and why tail sampling forces it

```text
   ┌── agent collectors (one per host/pod) ──┐
   │  receive local OTLP, batch, light filter │ ── no whole-trace view ──┐
   └──────────────────────────────────────────┘                          │
                                                                          ▼
                              ┌──────────── GATEWAY tier ────────────────────────┐
                              │  load-balancing exporter routes by trace_id  ──►  │
                              │  tail_sampling (sees WHOLE traces) ──► backend    │
                              └────────────────────────────────────────────────────┘
```

**Why tail sampling lives at the gateway, not the agent:** an agent only sees the spans emitted on its own host. A trace crosses many services on many hosts, so no single agent ever sees the whole trace. Tail sampling must run where *all spans of a given `trace_id` converge*. You achieve that with a **load-balancing exporter** that routes spans to gateway instances *by `trace_id`* — so every span of one trace lands on the same gateway, which can then make a correct whole-trace decision. Without this routing, scaling the gateway horizontally silently breaks tail sampling: each instance sees a fragment, and "keep all errors" misses the errors whose span landed elsewhere.

This is the operational fact that distinguishes a working tracing deployment from a broken one at scale: **head sampling scales freely; tail sampling requires trace-ID-aware routing into a co-located decision tier.**

---

## Reducing Cost Without Losing Signal

Sampling is one lever. These are the others, ordered by leverage.

- **Aggregate at the source.** A counter incremented a billion times is *one series*; a billion log lines is a billion stored records. Convert "log every request" into "increment a metric per request" and keep logs/traces for the exceptional cases. The biggest savings come from not emitting raw streams you only ever look at in aggregate.
- **Log levels & dynamic filtering.** DEBUG off in prod by default; make the level changeable at runtime, not only by deploy. Use the Collector `filter` processor to drop known-noisy logs (health checks, readiness probes) before they're billed.
- **Structured-log field pruning.** Drop fat fields you never query (full request/response bodies, verbose stack frames on non-errors) in the `attributes` processor. A 1.2 KB line trimmed to 400 B is a two-thirds cut with no loss of the fields you actually search.
- **Span dropping / filtering.** Not every span earns its keep. Internal framework spans, repetitive cache-hit spans, and health-check traces can be dropped with the `filter` processor while keeping the spans that explain latency.
- **Exemplars as the cheap bridge.** Instead of keeping expensive traces to explain a metric spike, attach an *exemplar* — a `trace_id` pointer — to the cheap metric sample. You get "show me one real example of this p99 spike" without paying trace prices for every request. Exemplars are the single best cost/fidelity trade in the toolkit: aggregate cost with on-demand drill-down.

The unifying principle: **keep the aggregate cheap, keep one example per aggregate, drop the rest.** The `caching-strategies` skill's instinct applies here too — you're caching the *representative*, not the whole population.

---

## Retention & Downsampling Tiers

You almost never need 90 days of full-resolution data. Tier it.

| Tier | Resolution | Retention | Cost | Use |
|---|---|---|---|---|
| **Hot** | full (e.g. 15s) | 7–15 days | high (fast storage, indexed) | active debugging, current dashboards |
| **Warm** | downsampled (e.g. 5m) | 30–90 days | medium | trend analysis, capacity planning |
| **Cold** | heavily rolled up (e.g. 1h) | 1–2 years | low (object storage) | year-over-year, compliance |

**Metric downsampling / rollups.** Old high-resolution points are aggregated into coarser ones: 15-second samples become 5-minute averages/max/min. You lose the ability to see a 30-second spike from six months ago — which you almost never need — and cut long-term storage by 20× or more. Tools like Thanos, Cortex, and Mimir do this automatically; vanilla Prometheus relies on **recording rules** to precompute rolled-up series.

**Recording rules for downsampling.** A recording rule precomputes an expensive or high-resolution query into a new, cheaper series at a longer evaluation interval. The rolled-up series is what your long-range dashboards and your cold tier read — far cheaper than re-aggregating raw data at query time.

The discipline: match retention to *how far back you actually look*, not to "more is safer." The fidelity floor (errors, audit, SLO, billing) may have its own legally mandated retention — that's a separate, non-negotiable track.

---

## Code Examples

### Full trace pipeline — `memory_limiter` + `tail_sampling` (errors + latency + 1%)

```yaml
# gateway-collector.yaml — runs in the GATEWAY tier (sees whole traces)
receivers:
  otlp:
    protocols: { grpc: {}, http: {} }

processors:
  # 1. ALWAYS first: shed load before RAM exhaustion. Tail sampling buffers
  #    every in-flight trace, so this guard is what keeps the collector alive.
  memory_limiter:
    check_interval: 1s
    limit_percentage: 80          # start refusing data at 80% of the RAM limit
    spike_limit_percentage: 25

  # 2. Tail sampling: decide AFTER the trace completes.
  tail_sampling:
    decision_wait: 10s            # buffer each trace up to 10s before deciding
    num_traces: 200000            # max traces held in memory at once
    expected_new_traces_per_sec: 50000
    policies:
      - name: keep-all-errors
        type: status_code
        status_code: { status_codes: [ERROR] }      # NEVER sample errors
      - name: keep-slow-traces
        type: latency
        latency: { threshold_ms: 2000 }             # keep everything over 2s
      - name: sample-the-rest
        type: probabilistic
        probabilistic: { sampling_percentage: 1 }   # 1% of normal traffic

  # 3. Batch LAST, just before export.
  batch: { send_batch_size: 8192, timeout: 5s }

exporters:
  otlp/backend:
    endpoint: backend:4317

service:
  pipelines:
    traces:
      receivers:  [otlp]
      processors: [memory_limiter, tail_sampling, batch]   # order matters
      exporters:  [otlp/backend]
```

### Probabilistic (head-style) sampler — a flat, stateless cost cap

```yaml
processors:
  probabilistic_sampler:
    sampling_percentage: 10       # keep 10%, decided by hashing trace_id
    # hash_seed must MATCH across all collectors for consistent decisions
    hash_seed: 22
```

Because the decision is a hash of the `trace_id`, the same trace is kept or dropped identically everywhere the same `hash_seed` is configured — consistent sampling, for free.

### `attributes` processor — delete a high-cardinality label

```yaml
processors:
  attributes/drop-userid:
    actions:
      - key: user_id
        action: delete            # strip the cardinality bomb from metrics
      - key: session_id
        action: delete
```

The same `user_id` stays valuable as a *trace* attribute or *log* field — this only removes it from the metrics pipeline where cardinality is lethal.

### `filter` processor — drop noisy health-check spans

```yaml
processors:
  filter/drop-healthchecks:
    error_mode: ignore
    traces:
      span:
        # OTTL: drop spans for health/readiness endpoints
        - 'attributes["http.route"] == "/healthz"'
        - 'attributes["http.route"] == "/readyz"'
        - 'name == "GET /metrics"'
```

Health checks are high-volume and never interesting; dropping them at the agent removes a large slice of trace volume before it's ever billed.

### Prometheus recording rule — downsample for the long-range tier

```yaml
# rules/downsample.yml — precompute a rolled-up, cheaper series
groups:
  - name: request_rate_5m
    interval: 5m                  # evaluate every 5 minutes, not every scrape
    rules:
      - record: job:http_requests:rate5m
        expr: sum by (job, route, status_class) (rate(http_requests_total[5m]))
```

The new `job:http_requests:rate5m` series is what your 90-day dashboards read — cheap to store and instant to query, versus re-aggregating raw counters across months.

### SDK-side head sampler — Go, `ParentBased(TraceIDRatioBased)`

```go
import (
	"go.opentelemetry.io/otel/sdk/trace"
)

// Keep ~5% at the SDK as a cheap raw-volume cap. ParentBased ensures a
// child span respects the PARENT's decision, so a trace is never half-kept
// across services — the SDK-side root of consistent sampling.
tp := trace.NewTracerProvider(
	trace.WithSampler(
		trace.ParentBased(trace.TraceIDRatioBased(0.05)),
	),
	trace.WithBatcher(exporter),
)
```

`TraceIDRatioBased` hashes the `trace_id`, so the decision is deterministic; `ParentBased` makes downstream services honour the upstream decision. Pair this cheap SDK cap with gateway tail sampling: the SDK trims raw volume, the gateway ensures the survivors are the useful ones.

---

## Best Practices

1. **Never sample away errors, audit/security events, SLO signals, or billing.** Encode this as a `status_code: [ERROR]` keep-100% policy so it's enforced, not just intended.
2. **`memory_limiter` is the first processor in every pipeline.** Tail sampling buffers in-flight traces; without the guard, the collector OOMs under exactly the spike it exists to handle.
3. **Put tail sampling in the gateway tier and route by `trace_id`.** A load-balancing exporter must converge each trace's spans on one instance, or "keep all errors" silently misses errors.
4. **Compute the cardinality product before shipping any metric label.** If the product can grow with users/traffic, it's not a label — move identity to traces/logs/exemplars.
5. **Control cost in the Collector, by config push.** Keep the app emitting; never hard-code sample rates in application code where changing them needs a deploy.
6. **Use head and tail together:** a cheap SDK/`probabilistic_sampler` cap for raw volume, gateway tail to make the survivors useful.
7. **Tier retention to how far back you actually look.** Hot full-resolution for days, downsampled warm for weeks, rolled-up cold for compliance.
8. **Alert on telemetry spend and series count**, not just on the system. A new high-cardinality label should page *you* before it pages finance.

---

## Edge Cases & Pitfalls

- **Tail sampling behind a naive load balancer.** Round-robin routing splits a trace's spans across gateways; none sees the whole trace; error policies miss errors. You need `trace_id`-aware routing (the load-balancing exporter), not generic L4 balancing.
- **`memory_limiter` placed late or omitted.** It only protects processors *after* it. Late = useless. Omitted = OOM crash-loop under load, going blind when you most need the data.
- **Dropping a label an alert depends on.** Strip `status_class` to save cardinality and your error-rate alert goes silent. Audit which queries depend on a label before deleting it.
- **`decision_wait` shorter than your slowest trace.** If a trace takes 12s and `decision_wait` is 10s, it's decided before the slow span arrives — the slow trace you wanted is sampled away. Set `decision_wait` above your p99.9 trace duration.
- **Inconsistent `hash_seed` across `probabilistic_sampler` instances.** Different seeds → different decisions for the same trace → half-kept traces. Same seed everywhere.
- **Downsampling the fidelity-floor metrics.** Rolling up your SLO error-budget metric corrupts the number your reliability program runs on. Exclude fidelity-floor signals from aggressive downsampling.
- **Counting from sampled data without `1/sample_rate`.** Rate-limiting sampling makes the effective rate *vary*, so a fixed multiplier is wrong — you need per-trace adjusted counts. (Maths: [`senior.md`](senior.md).)

---

## Common Mistakes

1. **Tail sampling at the agent tier.** An agent never sees the whole trace; the decision is made on a fragment. Tail belongs at a trace-ID-routed gateway.
2. **No `memory_limiter`**, then surprise when the buffering collector OOMs under load.
3. **`batch` before `tail_sampling`.** You batch *survivors*, not candidates — sampling must run first.
4. **Stripping a label without checking dependent alerts/dashboards**, going blind on error rate.
5. **Identity (`user_id`, `request_id`, full URL) as a metric label.** The #1 cardinality explosion; belongs on traces/logs/exemplars.
6. **Hard-coding sample rates in app code**, so tuning cost needs a redeploy.
7. **One flat retention for everything**, paying hot-tier prices for year-old data nobody queries.
8. **Cutting cost by deleting the signals you need** — gaming "reduce telemetry spend" by sacrificing fidelity (Goodhart). Cross-ref Engineering Metrics & DORA.

---

## Tricky Points

1. **Processor order is behaviour.** `memory_limiter` first, `batch` last, sampling before batch, label-drop before the metric is counted. The same processors in a different order do a different thing.
2. **Head sampling scales freely; tail sampling does not.** Head is stateless and embarrassingly parallel. Tail needs trace-ID-aware routing and per-trace memory — adding gateway replicas without the routing *breaks* it.
3. **`probabilistic_sampler` is deterministic, not random.** It hashes the `trace_id`, so with a shared `hash_seed` it's consistent across services — the same property tail sampling gets by deciding centrally.
4. **Exemplars give you trace-level drill-down at metric-level cost** — the single best cost/fidelity trade. Keep the aggregate cheap, attach one example.
5. **Adjusted counts depend on the sampler.** A fixed-rate sampler → multiply by `1/rate`. A rate-*limiting* sampler → the rate varies, so each kept trace carries its own weight. Mixing them naively corrupts your totals. (Full maths: [`senior.md`](senior.md).)
6. **Downsampling is lossy on purpose.** A 5-minute rollup cannot show a 30-second spike from last quarter. That's the right trade for trends — and the wrong trade for an SLO metric you debug at high resolution.

---

## Apply it

1. Find a real component where **Telemetry Cost & Sampling Strategy** affects an interface or dependency.
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

- Which boundary is most affected by Telemetry Cost & Sampling Strategy?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
