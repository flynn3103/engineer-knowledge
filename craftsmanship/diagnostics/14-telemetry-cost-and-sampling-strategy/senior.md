# Telemetry Cost & Sampling Strategy — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Telemetry Cost & Sampling Strategy** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Topic:** [Telemetry Cost & Sampling Strategy Roadmap](README.md)
> **Focus:** The two ideas that separate a sampling setup that *works* from one that lies to you: making the keep/drop decision a deterministic function of the `trace_id` so traces are never half-sampled, and carrying the per-item sample rate so you can reconstruct true counts from a thinned stream. Consistency and statistical correctness — the math the bill-cutting depends on.

---

## Core Concepts

### 1. A sampling decision must be a function of the trace, not of the moment

If each service flips its own coin, the same trace gets different verdicts in different places, and you store traces full of holes. The only robust design makes the decision **derive from the `trace_id` itself** — a value every service already shares — so the verdict is identical everywhere by construction, with zero coordination.

### 2. You cannot recover what you didn't weight

The instant you sample, the surviving stream is a *biased sample of itself* (especially under dynamic sampling, where errors survive at 100% and normal traffic at 1%). The only way to get a true count back is to have recorded, on each kept item, the rate at which it was kept — then sum `1/rate`. If the rate wasn't stored at sample time, the truth is unrecoverable. **The sample rate is data; treat it like the payload.**

### 3. Harder sampling buys cost with variance

Estimates from sampled data have error, and that error grows as the rate shrinks. A 10% sample estimates a rare event far more tightly than a 0.1% sample. Sampling is not free fidelity-wise even when you weight correctly — it trades *certainty* for *cost*, and you must know roughly how much.

### 4. Head and tail are not rivals — they compose

Head sampling caps raw volume cheaply and consistently (it's a `trace_id` hash). Tail sampling makes the survivors *useful* (keep errors and slow traces). Mature systems run both: a cheap deterministic head cap at the SDK, a smart tail policy at the gateway. The two rates *multiply*, which is exactly where adjusted-count math gets subtle.

### 5. The fidelity floor is encoded, not remembered

"Never sample errors" is a sentence at junior level and a *policy in the config* at senior level — a `status_code: [ERROR]` keep-100% rule, an SLO-signal exclusion from downsampling, an audit pipeline that bypasses the sampler entirely. If the floor depends on a human remembering it, it will be violated.

### 6. Cardinality has a budget you enforce in the collector, not a wish

Identity belongs on traces, not metrics. The control point is the collector: allow-lists, `metric_relabel_configs` drops, attribute limits — backed by an alert on series count so the next bomb pages you before it OOMs the TSDB.

---

## Consistent / Deterministic Sampling

This is the senior centerpiece. A trace crosses many services; each makes a sampling decision; if those decisions disagree, you get a **half-sampled trace** — service A's spans present, service B's spans gone — which is *worse than dropping the whole trace*, because it looks complete and misleads you.

### The mechanism: hash the trace_id against a threshold

The decision must be a pure function of the `trace_id`, so every service reaches the same verdict independently. Concretely:

```text
keep the trace  ⟺  hash(trace_id)  <  threshold
where             threshold = sample_rate × MAX

MAX        = the maximum value the hash can produce (e.g. 2^56, or 1.0 normalized)
sample_rate= the fraction you want to keep, e.g. 0.01 for 1%
```

Because `hash(trace_id)` is deterministic, *every service computes the same hash for the same trace* and compares it to the *same* threshold. There is no coordination, no shared state, no network call — yet every service agrees. A trace is kept *whole* or dropped *whole*, never split.

```text
trace_id = abc123…   hash → 0.0047  (normalized to [0,1))
sample_rate = 0.01   threshold = 0.01
0.0047 < 0.01  → KEEP   (in service A, B, C — all compute 0.0047 < 0.01 → KEEP)

trace_id = def456…   hash → 0.83
0.83 < 0.01  → DROP     (dropped identically in every service)
```

This is also why the property *nests*: a 1% sample is a strict subset of a 10% sample, because `hash < 0.01` implies `hash < 0.10`. You can lower the rate later and the kept set shrinks coherently — no churn, no re-randomization.

### Propagating the decision: ParentBased + the sampled flag

Hashing gives every *independent* service the same answer, but the more robust pattern is to make the **root** decide and everyone downstream **inherit** it. W3C Trace Context carries the decision on the wire: the `traceparent` header's trace-flags has a **sampled bit**, and `tracestate` can carry vendor sampling state. A downstream service reads the parent's flag and honours it rather than re-deciding.

OTel's samplers compose exactly this:

- **`TraceIDRatioBased(p)`** — the *root* sampler: makes the deterministic hash-threshold decision at ratio `p`.
- **`ParentBased(root=...)`** — wraps it: if there's a parent, honour the parent's sampled flag; if this span *is* the root, fall back to `TraceIDRatioBased`.

So the root service hashes and decides once; every downstream service sees the sampled flag in the incoming context and keeps or drops to match. Result: one decision, propagated, never contradicted. **`ParentBased(TraceIDRatioBased(p))` is the canonical consistent-sampling SDK config**, and it's why a trace is whole or absent, never half-there.

> The senior failure this prevents: independent per-service rates. If A samples at 5% and B at 1% with no propagation, the traces that survive *both* are the intersection (~0.05%), and the rest are fragments. Propagate one decision; don't intersect many.

---

## Head vs Tail in Production

Middle level distinguished them; senior level decides *when each, and how they combine*.

| Question | Use head | Use tail | Use both |
|---|---|---|---|
| Need a hard, cheap volume cap? | ✅ | | |
| Must keep 100% of errors/slow? | | ✅ | |
| Massive multi-service fleet? | ✅ (scales free) | (needs routing) | ✅ |
| Want cheap raw cap *and* useful survivors? | | | ✅ (the norm) |

**The standard production shape:** a cheap deterministic **head** sample at the SDK (`ParentBased(TraceIDRatioBased)`) to trim the firehose before it's even shipped, then **tail** sampling at the gateway to guarantee the survivors include every error and slow trace. Head controls *cost*; tail controls *fidelity of what's kept*.

### Rate-limiting and priority sampling

A flat percentage still blows the budget during a flash sale (1% of 10× traffic is 10× the cost). **Rate-limiting** sampling caps at *N traces/second* instead — absolute cost control, at the price of a sample rate that now *varies with traffic* (which is why you must record per-item rates, below). **Priority sampling** keeps high-value keys (paying customers, checkout) at higher rates than low-value ones.

### Dynamic sampling (Honeycomb-style)

The most powerful production pattern: **vary the sample rate by a key** so rare keys are kept at high rates and common keys at low rates. Bucket events by a key (e.g. `endpoint + status`), measure each key's recent volume, and set that key's rate *inversely* to its frequency:

```text
key = "/checkout 200"   high volume (900k/min)  → sample 1 in 1000   (rate 0.001)
key = "/checkout 500"   rare       (40/min)     → sample 1 in 1      (rate 1.0, keep all)
key = "/admin   200"    rare       (10/min)     → sample 1 in 1      (keep all)
```

You keep *every* instance of rare-but-interesting keys and aggressively thin the common boring ones — the right traffic, not just less traffic. The catch: **each kept event now has a different sample rate**, so you *must* record that rate per event or every count you derive is wrong (next section).

---

## Statistical Correctness of Sampling

The other senior centerpiece. Sampling throws data away; the question is whether you can still compute true numbers from what's left. You can — **only if you record the sample rate of each kept item** — via *adjusted counts*.

### The core formula

```text
estimated true count  =  Σ  (1 / sample_rate_of_that_item)
                       kept items

Each kept item carries weight 1/sample_rate. A 1%-sampled item represents
100 real items (itself + 99 dropped). Sum the weights → estimate the total.
```

If every item shares one rate `p`, this collapses to the familiar `kept_count × (1/p)`. But under **dynamic** or **rate-limiting** sampling, rates *vary per item*, and a single multiplier is flat wrong — you must weight each item by *its own* recorded rate.

### Worked mixed-rate example

A checkout stream with dynamic sampling: **errors kept at 100% (rate 1.0, weight 1)**, **normal traffic kept at 1% (rate 0.01, weight 100)**. In one minute the collector keeps:

```text
KEPT (what's in the backend):
  120  error traces      each sampled at rate 1.0  → weight   1   each
  900  normal traces     each sampled at rate 0.01 → weight 100   each
```

**Reconstruct the true total requests:**

```text
true total = Σ (1/rate)
           = (120 × 1) + (900 × 100)
           = 120 + 90,000
           = 90,120 requests   ← the real traffic that minute
```

**Reconstruct the true error count:**

```text
true errors = Σ over kept ERROR traces of (1/rate)
            = 120 × 1            (errors were kept at 100%, weight 1)
            = 120 errors        ← exact, because we kept them all
```

**Reconstruct the true error rate:**

```text
error rate = true_errors / true_total
           = 120 / 90,120
           = 0.00133  →  0.133%
```

### What goes wrong if you forget the weights

Count the survivors naively:

```text
naive total  = 120 + 900 = 1,020 "requests"          (off by 88× — true is 90,120)
naive errors = 120                                    (happens to be right — kept at 100%)
naive rate   = 120 / 1,020 = 11.8%                    ← reported error rate is ~88× too high
```

The naive error rate reads **11.8%** when reality is **0.133%** — because the errors are *over-represented* in the kept stream (100% of them survived) while normal traffic is *under-represented* (1% survived). **Dynamic sampling makes the unweighted error rate catastrophically wrong in the alarming direction** — a false outage. Only weighting by the recorded per-item rate recovers 0.133%.

### Variance: the cost of sampling harder

Even weighted correctly, the estimate has error, and it grows as you sample harder. The standard error of a count estimated from a sample of rate `p` scales roughly like:

```text
relative error  ≈  1 / sqrt(expected_kept_count)

keep 10,000 items → ~1% relative error    (tight)
keep    100 items → ~10% relative error   (loose)
keep     10 items → ~32% relative error   (basically a guess)
```

So a 0.01% sample of a rare endpoint may keep *zero* items some minutes and estimate "0 requests" — wildly wrong. The senior rule: **sample common traffic hard, rare-but-important traffic lightly or not at all** (which is exactly what dynamic sampling does), and never trust a count whose *expected kept count* is in the single digits.

> The one-line takeaway: **carry the sample rate, weight by `1/rate`, and respect that harder sampling = more variance.** Without the recorded rate, none of this is possible — the truth left with the dropped spans.

---

## The Fidelity Floor

Some signals are kept at 100%, full stop. At senior level this isn't a guideline — it's *encoded in the pipeline* so it can't be forgotten.

| Signal | Why never sampled | How the floor is encoded |
|---|---|---|
| **Errors** | The trace you'll actually open; sampling them away defeats tracing | `tail_sampling` `status_code: [ERROR]` keep-100% policy |
| **Security / audit events** | Sampling away an audit log can be *illegal*; security needs the full record | A dedicated pipeline that **bypasses the sampler entirely** |
| **SLO-relevant signals** | They define your error budget; a sampled SLO number is a corrupt one | Excluded from sampling *and* from aggressive downsampling |
| **Billing / usage data** | Under-counting revenue events is a financial defect, not a telemetry one | Exact pipeline, no sampling, often a separate durable store |

The danger is concrete: a flat 1% head sample keeps ~1% of errors — so the *one* trace explaining last night's outage is 99% likely already deleted before you log in. The floor exists so that the thing you'll need at 3 a.m. is guaranteed present.

**How tail policies encode it:** the floor becomes the *first, highest-priority* policies in the `tail_sampling` processor — errors kept, latency outliers kept, SLO-tagged traces kept — and only the *residual* "everything else" is probabilistically thinned. The composite/and policies (in Code Examples) are how you express "keep this trace if it's an error OR slow OR over budget, else sample at 1%."

---

## Cardinality Governance

Metrics cost is cardinality, and at senior level you *govern* it — enforce a budget, don't hope for one.

- **Allow-lists in the collector.** User-supplied or external label values pass through a fixed allow-list; anything unknown collapses to `other`. The unbounded source is capped at the pipeline, centrally.
- **`metric_relabel_configs` to drop or aggregate.** The Prometheus scrape-time lever: `drop` a high-cardinality label outright, or `labeldrop` it to *aggregate* the series down. Dropping removes a dimension; aggregating merges series that now share a label set.
- **Dropping vs aggregating.** Dropping `user_id` removes the dimension entirely. *Aggregating* keeps the metric but sums across the dropped dimension — you lose per-user breakdown but keep the totals. Choose by what your queries need.
- **Exemplars offload high cardinality to traces.** Keep the metric low-cardinality and attach a `trace_id` *exemplar*; per-user/per-request drill-down lives in traces, where cardinality is cheap because nothing is pre-aggregated into permanent series.
- **A cardinality budget you enforce.** A real number per service ("`checkout` may emit ≤ 50,000 active series"), with an alert at 80% and a per-metric series-count alert so one runaway metric is caught before it eats the whole budget. (Full treatment: [Metrics — Senior](../04-metrics/senior.md).)

---

## The OTel Collector Topology

Consistent tail sampling *forces* a two-tier topology, because a tail decision needs the whole trace and a trace's spans are emitted across many hosts.

```text
  ┌── AGENT collectors (one per host/pod) ──┐
  │  receive local OTLP, memory_limiter,     │
  │  light filter/batch — NO whole-trace view│
  └───────────────┬──────────────────────────┘
                  │  loadbalancing exporter, routing_key: traceID
                  ▼  (every span of one trace → the SAME gateway)
  ┌──────────────── GATEWAY tier ───────────────────────────┐
  │  memory_limiter  →  tail_sampling (sees WHOLE traces)    │
  │  →  batch  →  backend exporter                            │
  └──────────────────────────────────────────────────────────┘
```

- **Agent → gateway.** Agents fan in cheaply and locally; they cannot tail-sample because no agent sees a whole trace.
- **Loadbalancing exporter, `routing_key: traceID`.** This is what makes tail sampling correct at scale: it hashes the `trace_id` to pick a gateway, so *all spans of one trace land on the same gateway*, which can then decide on the complete trace. Generic L4/round-robin routing splits a trace across gateways and silently breaks "keep all errors."
- **`memory_limiter` first.** Tail sampling buffers every in-flight trace; without the limiter the gateway OOMs under exactly the spike it exists to survive.
- **Sizing `decision_wait` and `num_traces`.** `decision_wait` must exceed your slowest *realistic* trace (above p99.9 trace duration) or slow traces are decided before their slow span arrives — and sampled away. `num_traces` bounds the buffer: roughly `expected_new_traces_per_sec × decision_wait`, with headroom; too small and traces are evicted (lost) before the decision window closes.

---

## Code Examples

### Tail sampling with composite / and policies — fidelity floor + rate-limited rest

```yaml
# gateway-collector.yaml — GATEWAY tier (sees whole traces)
processors:
  memory_limiter:
    check_interval: 1s
    limit_percentage: 80
    spike_limit_percentage: 25

  tail_sampling:
    decision_wait: 12s              # MUST exceed slowest realistic trace
    num_traces: 600000             # ≈ expected_new_traces_per_sec × decision_wait, + headroom
    expected_new_traces_per_sec: 50000
    policies:
      # --- FIDELITY FLOOR: highest priority, keep 100% ---
      - name: keep-all-errors
        type: status_code
        status_code: { status_codes: [ERROR] }

      - name: keep-latency-outliers
        type: latency
        latency: { threshold_ms: 2000 }

      # AND policy: keep enterprise-tier traffic that is also slow-ish
      - name: keep-slow-enterprise
        type: and
        and:
          and_sub_policy:
            - name: is-enterprise
              type: string_attribute
              string_attribute: { key: customer.tier, values: [enterprise] }
            - name: somewhat-slow
              type: latency
              latency: { threshold_ms: 500 }

      # --- RESIDUAL: rate-limit normal traffic to an absolute cap ---
      - name: rate-limit-the-rest
        type: rate_limiting
        rate_limiting: { spans_per_second: 1500 }

  batch: { send_batch_size: 8192, timeout: 5s }

service:
  pipelines:
    traces:
      receivers:  [otlp]
      processors: [memory_limiter, tail_sampling, batch]   # order is behaviour
      exporters:  [otlp/backend]
```

The policies OR together: a trace is kept if it errored, *or* was slow, *or* matches the `and` (enterprise **and** ≥500ms), *or* survives the rate limiter. The floor sits first; only the residual is thinned.

### Loadbalancing exporter — route spans to the gateway tier by trace_id

```yaml
# agent-collector.yaml — runs on every host; routes WHOLE traces to one gateway
exporters:
  loadbalancing:
    routing_key: traceID           # ALL spans of one trace → the same gateway
    protocol:
      otlp:
        tls: { insecure: true }
    resolver:
      dns:
        hostname: otel-gateway.observability.svc.cluster.local
        port: 4317

service:
  pipelines:
    traces:
      receivers:  [otlp]
      processors: [memory_limiter, batch]
      exporters:  [loadbalancing]   # NOT a generic LB — must route by traceID
```

`routing_key: traceID` is the line that makes gateway tail sampling correct. Without it, a trace's spans scatter across gateways and each gateway decides on a fragment.

### OTel SDK — `ParentBased(TraceIDRatioBased)` consistent head sampler (Python)

```python
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.sampling import (
    ParentBased, TraceIdRatioBased,
)

# Root services hash the trace_id at 5% (deterministic, consistent everywhere).
# ParentBased: downstream services HONOUR the parent's sampled flag instead of
# re-deciding — so a trace is whole or absent, never half-sampled.
provider = TracerProvider(
    sampler=ParentBased(root=TraceIdRatioBased(0.05))
)
```

The root makes one deterministic decision; the W3C `traceparent` sampled flag propagates it; every child honours it via `ParentBased`. This is consistent sampling at the SDK.

### Prometheus — drop a high-cardinality label via `metric_relabel_configs`

```yaml
scrape_configs:
  - job_name: checkout
    metric_relabel_configs:
      # Drop the cardinality-bomb label from EVERY series of this metric.
      - source_labels: [__name__]
        regex: 'checkout_duration_seconds.*'
        action: keep
      - regex: 'user_id|session_id|request_id'   # strip identity labels
        action: labeldrop                         # aggregate away the dimension
```

`labeldrop` *aggregates* series down by removing the dimension (keeps the metric, loses per-user breakdown). Use `drop` instead to discard whole series matching a predicate. Identity moves to traces via exemplars.

### Recording rule + retention/downsampling tier

```yaml
# rules/downsample.yml — precompute a rolled-up, cheap series for the warm tier
groups:
  - name: request_rate_5m
    interval: 5m                    # evaluate every 5m, not every scrape
    rules:
      - record: job:http_requests:rate5m
        expr: sum by (job, route, status_class) (rate(http_requests_total[5m]))
# Retention tiers (Thanos/Mimir): hot 15s/15d → warm 5m/90d → cold 1h/2y.
# NEVER downsample fidelity-floor metrics (SLO error budget, billing).
```

---

## Worked Example — Reconstructing Truth From a Sampled Stream

**Setup.** A payments gateway uses dynamic sampling with three rates, recorded per trace as `sampling.rate`:

```text
KEPT in the backend over one hour:
  group          kept count   recorded sample_rate   weight (1/rate)
  errors (5xx)        430            1.00                1
  slow (>2s)          610            0.50                2      (kept 1 in 2)
  normal             8,200           0.005             200      (kept 1 in 200)
```

**Step 1 — true total requests** = Σ (kept × weight):

```text
errors:  430   × 1   =      430
slow:    610   × 2   =    1,220
normal:  8,200 × 200 = 1,640,000
────────────────────────────────
true total           ≈ 1,641,650 requests
```

**Step 2 — true error count.** Errors were kept at 100% (weight 1), so the kept count *is* the true count — no scaling needed:

```text
true errors = 430 × 1 = 430   (exact — fidelity floor kept them all)
```

**Step 3 — true error rate:**

```text
error rate = 430 / 1,641,650 = 0.0000262 → 0.0026%
```

**Step 4 — what breaks without weights.** Count survivors naively:

```text
naive total  = 430 + 610 + 8,200 = 9,240
naive rate   = 430 / 9,240 = 4.65%
```

The unweighted dashboard reports a **4.65% error rate**; the truth is **0.0026%** — wrong by ~1,800×, and in the panic direction. The errors and slow traces, kept at far higher rates than normal traffic, dominate the raw survivor count and manufacture a fake incident.

**Lessons:**

1. **The weight (`1/sample_rate`) must be recorded per trace at sample time.** Here it lives in `sampling.rate`. Without it, Steps 1 and 3 are impossible.
2. **Mixed rates make naive counts not just wrong but *directionally alarming*** — over-represented errors inflate the apparent error rate.
3. **Fidelity-floor signals (errors) need no upscaling** precisely because they're kept at 100% — the weight is 1.
4. The whole reconstruction is *write-time-dependent*: the correctness was decided when the sampler stamped the rate onto the span, exactly like a histogram's accuracy is decided at bucket-design time.

---

## Coding Patterns

### Pattern 1 — Consistent decision = hash(trace_id) vs threshold

```text
keep ⟺ hash(trace_id) < sample_rate × MAX
same trace_id → same hash → same decision in EVERY service. No coordination.
```

### Pattern 2 — Propagate, don't re-decide

```python
sampler = ParentBased(root=TraceIdRatioBased(0.05))
# children honour the parent's sampled flag; only the root hashes & decides.
```

### Pattern 3 — Stamp the sample rate onto every kept item

```text
on keep:  span.set_attribute("sampling.rate", p)   # or weight = 1/p
# WITHOUT this, no count derived later can be corrected. The rate is data.
```

### Pattern 4 — Upsample with adjusted counts

```text
true_total  = Σ over kept of (1 / sampling.rate)
true_metric = Σ over kept matching predicate of (1 / sampling.rate)
# fixed-rate → kept × (1/p);  dynamic/rate-limited → per-item weights (rate VARIES)
```

### Pattern 5 — Encode the fidelity floor as the first policies

```yaml
policies:
  - { name: keep-errors,  type: status_code, status_code: {status_codes: [ERROR]} }
  - { name: keep-slow,    type: latency,     latency: {threshold_ms: 2000} }
  - { name: sample-rest,  type: probabilistic, probabilistic: {sampling_percentage: 1} }
```

### Pattern 6 — Route by trace_id so tail sees whole traces

```yaml
exporters: { loadbalancing: { routing_key: traceID, ... } }
# generic LB → split traces → missed errors. trace_id routing → whole traces.
```

---

## Clean Code

- **The sampling decision is a pure function of the `trace_id`,** never of wall-clock, per-service RNG, or local state. Same ID, same verdict, everywhere.
- **Every kept span carries its sample rate** (`sampling.rate` or an explicit weight). The rate is treated as payload, not metadata to add "later."
- **The fidelity floor is config, not a comment:** `status_code: [ERROR]` keep-100%, audit pipeline bypassing the sampler, SLO signals excluded from sampling *and* downsampling.
- **Adjusted-count math weights per item** under dynamic/rate-limiting sampling; a single `1/p` multiplier appears *only* where the rate is genuinely uniform.
- **`ParentBased` wraps the ratio sampler** so downstream services inherit rather than re-decide; no service independently re-rolls a trace's fate.
- **`decision_wait` exceeds p99.9 trace duration** and `num_traces` is sized from `rate × decision_wait`, with the values commented against the traffic they assume.
- **Identity lives on traces/exemplars, never metric labels;** the cardinality budget is a documented number with an enforcing alert.

---

## Best Practices

1. **Make sampling consistent by `trace_id`** — `ParentBased(TraceIDRatioBased)` at the SDK, shared `hash_seed` for any collector-side probabilistic sampler. Whole traces or none.
2. **Record the sample rate on every kept item**, always. It's the only thing that makes adjusted counts possible, and it's unrecoverable after the fact.
3. **Weight by `1/sample_rate` for every count, rate, or total** derived from sampled data — per item when rates vary (dynamic / rate-limiting).
4. **Encode the fidelity floor in the pipeline** — errors/slow kept 100% as the first tail policies; audit/billing bypass sampling entirely; SLO signals excluded from sampling and downsampling.
5. **Run head + tail together:** deterministic head cap for cost, gateway tail for fidelity of the survivors.
6. **Route by `trace_id` into a gateway tier** (loadbalancing exporter) and put `memory_limiter` first; size `decision_wait` above your slowest realistic trace.
7. **Govern cardinality with a budget you enforce** — allow-lists, `metric_relabel_configs` drop/aggregate, exemplars for drill-down, an alert at 80% of the per-service series budget.
8. **Sample common traffic hard, rare-but-important traffic lightly or never** (dynamic sampling) — and never trust a count whose expected kept count is single digits.

---

## Edge Cases & Pitfalls

- **Independent per-service rates.** Service A at 5%, B at 1%, no propagation → survivors are the ~0.05% intersection and the rest are fragments. Propagate one decision (`ParentBased`); don't intersect many.
- **Forgetting the rate under dynamic sampling.** A single `1/p` multiplier is *wrong* when rates vary — it over- or under-counts whichever group was sampled differently. Each item needs its own weight.
- **Naive error rate after dynamic sampling.** Errors kept at 100%, normal at 1% → the unweighted error rate is inflated ~`1/normal_rate`× (often 50–200×), manufacturing a fake outage. Always weight.
- **`decision_wait` shorter than the slowest trace.** A 14s trace under `decision_wait: 10s` is decided before its slow span lands — the slow trace you wanted is sampled away. Set above p99.9 trace duration.
- **`num_traces` too small.** Traces are evicted before the decision window closes; you lose traces silently under load. Size from `rate × decision_wait` + headroom.
- **Generic load balancing in front of tail sampling.** Splits traces across gateways; "keep all errors" misses errors whose span landed elsewhere. Route by `traceID`.
- **Downsampling or sampling the fidelity floor.** Rolling up the SLO error-budget metric, or sampling audit events, corrupts the numbers your reliability and compliance programs run on.
- **Sampling low-volume signals.** A 0.1% sample of a 10/min endpoint keeps ~0 — "keep everything" is cheaper *and* correct for tiny high-value streams.

---

## Common Mistakes

1. **Per-service coin flips** instead of a `trace_id`-derived decision → half-sampled, holey traces.
2. **Not recording the sample rate** → true counts permanently unrecoverable from the sampled stream.
3. **One `1/p` multiplier under dynamic/rate-limiting sampling** → silently wrong totals and a directionally alarming error rate.
4. **Tail sampling behind a generic load balancer** → split traces, missed errors. (Use `routing_key: traceID`.)
5. **`decision_wait` below the slowest trace** → the slow traces you most wanted are decided early and dropped.
6. **Fidelity floor as a wiki sentence**, not a `status_code: [ERROR]` policy / sampler-bypassing audit pipeline → the floor gets violated.
7. **Identity on metric labels** → cardinality explosion; belongs on traces/exemplars with a budgeted, alerted cap.
8. **Cutting cost by deleting fidelity** — gaming "reduce telemetry spend" by sacrificing the signals you need (Goodhart). Cross-ref Engineering Metrics & DORA.

---

## Tricky Points

1. **Consistent sampling needs *no* coordination.** It works precisely because the decision is a deterministic function of a value (`trace_id`) every service already has. The "shared state" is the ID itself.
2. **Lower rates nest inside higher rates** under hash-thresholding: `hash < 0.01` ⟹ `hash < 0.10`. Tightening the rate shrinks the kept set coherently — no re-randomization, no churn.
3. **`ParentBased` vs re-deciding.** Even with deterministic hashing, you propagate via the sampled flag rather than re-hash everywhere — it's robust to services that compute the hash slightly differently, and it lets a service *force* keep (e.g. it errored).
4. **Adjusted counts give you *unbiased estimates*, not exact truth.** The expectation is right; the variance is real and grows as `1/sqrt(kept)`. A correct method can still produce a noisy number from too few samples.
5. **Errors need no upscaling** *because* they're on the fidelity floor (rate 1.0, weight 1) — the kept count is the true count. The upscaling is for the thinned normal traffic.
6. **Rate-limiting makes the rate an output, not an input.** You set N/sec; the *effective rate* falls out of traffic. That's exactly why each item must carry the rate it was actually sampled at.

---

## Apply it

1. State the system invariant that **Telemetry Cost & Sampling Strategy** must protect.
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

- Which invariant must remain true when Telemetry Cost & Sampling Strategy fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
