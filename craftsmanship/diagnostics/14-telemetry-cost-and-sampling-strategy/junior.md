# Telemetry Cost & Sampling Strategy — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Telemetry Cost & Sampling Strategy** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Topic:** [Telemetry Cost & Sampling Strategy Roadmap](README.md)
> **Focus:** Why telemetry costs money, where the money goes for each of the three signals, and the one idea that controls trace cost — sampling. Head vs tail in plain terms. The one rule you must never break: don't sample away your errors.

---

## Core Concepts

### 1. Telemetry costs money to ship, store, and index — and the bill scales with volume, not value

You pay three times for one log line: to **transmit** it (network), to **store** it (disk, for the whole retention window), and often to **index** it (so you can search it fast). None of those costs care whether the line was ever useful. A vendor charges you the same for the DEBUG line nobody read as for the ERROR that explained an outage. That asymmetry — cost scales with *volume*, value does not — is the whole reason sampling and filtering exist.

### 2. The three signals fail expensive in three different ways

There is no single "telemetry cost" lever. **Metrics** explode through **cardinality** — every new label combination is a new time series to store forever. **Logs** explode through **volume** — bytes × retention. **Traces** explode through **volume × spans** — a single request can be 40 spans, and at high traffic that is a firehose. Knowing *which* driver is hurting tells you *which* lever to pull. Pulling the wrong one (e.g. shortening log retention to fix a metrics-cardinality bill) does nothing.

### 3. Sampling is keeping *some* and being honest about it

Sampling means: of all the traces (or logs) flowing through, keep a chosen fraction and drop the rest. The art is choosing *which* fraction. Keeping a random 1% is cheap but blind — you'll drop most of your errors too. Keeping *all errors plus a sample of normal traffic* costs more to compute but keeps the data you actually use. The honest part comes later: if you kept 1% and you want to report "total requests," you must multiply by 100 (see [`senior.md`](senior.md)).

### 4. Head sampling is blind; tail sampling can see

The deepest distinction in this whole topic: do you decide to keep a trace **before** it happens (head) or **after** (tail)? Head sampling is a coin-flip at the start — cheap, but the coin doesn't know the request is about to fail. Tail sampling waits, buffers all the spans, *looks* at the finished trace, and then keeps it if it's an error or slow. Tail sampling is the only way to guarantee "keep all the interesting traces," and it costs real memory and a collector to buffer.

### 5. Some signals you never sample

There is a floor below which you do not cut, no matter the bill: **errors, security/audit events, SLO-relevant signals, and billing data.** Sampling away an audit log can be illegal. Sampling away the error trace defeats the purpose of having traces. Sampling away an SLO signal corrupts the number your whole reliability program runs on. Cost control is about cutting the *boring high-volume* data, not the rare important data — those are opposites.

---

## Cost Drivers per Signal

The most important table in this roadmap. Memorise the middle column.

| Signal | Cost driver | The killer pattern | What it costs | The fix |
|---|---|---|---|---|
| **Metrics** | **Cardinality** — distinct label sets | a high-cardinality label (`user_id`, `request_id`, full URL, email) | one time series *per unique value* — millions of series | drop/allow-list labels; move identity to logs/traces/exemplars |
| **Logs** | **Volume** — bytes × retention | DEBUG on in prod; fat JSON fields; everything kept 90 days | ingest + storage scale with traffic, linearly and relentlessly | level control, field pruning, retention tiers |
| **Traces** | **Volume × spans/trace** | 100% sampling of deep traces at high rps | every request × every span, shipped and stored | head + tail sampling |

A worked number for the metrics killer (the one juniors hit first):

```text
metric:   http_request_duration_seconds  (a histogram, ~12 buckets + _sum + _count ≈ 14 series)
labels:   method (4 values) × status (6 values) × endpoint (20 values)
series:   14 × 4 × 6 × 20 = 6,720 time series           ← totally fine

Now someone adds  user_id  as a label, for 500,000 users:
series:   6,720 × 500,000 = 3,360,000,000 time series   ← 3.36 BILLION. Database dead.
```

The label call was free. The *cardinality* it created is the bill. (Full treatment with the collector fix in [`middle.md`](middle.md).)

---

## Head vs Tail Sampling

This is the heart of the topic. A concrete scenario makes the difference unforgettable.

> **Scenario.** Your checkout service handles **50,000 requests/second**, each producing a trace of ~30 spans. Keeping 100% is unaffordable. 0.3% of requests **error**; another 0.5% are **slow** (>2s). You want to keep your trace bill small *and* never lose an error or a slow request.

**Head-based sampling (probabilistic, 1%).** At the *start* of each trace, flip a weighted coin: keep with probability 0.01. Cheap, stateless, every service can do it independently. But the coin is flipped *before the request runs* — it has no idea this particular request is about to error or time out. Result: you keep ~1% of *everything*, which means you keep ~1% of your errors too — you **drop 99% of the exact traces you wanted.** Good for a flat cost cap; useless for "keep the interesting ones."

**Tail-based sampling.** The collector **buffers all spans of each trace** in memory until the trace completes, then applies policies to the *finished* trace:

```text
  policy 1: status == ERROR        → KEEP 100%   (saw the error)
  policy 2: duration > 2s          → KEEP 100%   (saw it was slow)
  policy 3: everything else        → KEEP 1%     (a representative sample)
```

Now you keep **every error, every slow request, and a 1% sample of normal traffic** — the cost of roughly 1.8% of traces instead of 1%, but you never lose the trace you'll actually open. The price: the collector must **hold every trace in memory** until it's complete (typically a few seconds' decision window) and must see *all* spans of a trace — which constrains your collector topology (a single trace's spans must reach the same collector instance).

| | **Head-based** | **Tail-based** |
|---|---|---|
| **When decided** | trace start | after trace completes |
| **Sees if interesting?** | No | Yes |
| **Memory cost** | ~zero | buffers every in-flight trace |
| **Needs all spans co-located?** | No | **Yes** (collector must see the whole trace) |
| **Keeps all errors?** | only ~sample_rate of them | **yes, 100%** |
| **Best for** | uniform cap, massive fleets, simplicity | keeping the traces that matter |

Most mature setups use **both**: a cheap head sample at the SDK to cap raw volume, then tail sampling in the collector to make sure the survivors are the *useful* ones. (Real config in [`middle.md`](middle.md); consistent decisions across services in [`senior.md`](senior.md).)

---

## Your First Sampling Config — Examples

The cost-control point is the **OpenTelemetry Collector**, configured in YAML. Here are the two starter processors.

### Probabilistic (head-style) sampling in the Collector

```yaml
# otel-collector-config.yaml
processors:
  # Keep ~10% of traces, blind to whether they're interesting. Cheap and stateless.
  probabilistic_sampler:
    sampling_percentage: 10        # 10% kept; the simplest cost cap there is

  batch: {}                        # always batch before export (efficiency)

service:
  pipelines:
    traces:
      receivers:  [otlp]
      processors: [probabilistic_sampler, batch]
      exporters:  [otlp]
```

### Tail sampling — keep all errors and all slow traces, sample the rest

```yaml
processors:
  tail_sampling:
    decision_wait: 10s             # buffer each trace up to 10s before deciding
    num_traces: 100000             # max traces held in memory at once
    policies:
      - name: keep-all-errors
        type: status_code
        status_code: { status_codes: [ERROR] }   # 100% of error traces
      - name: keep-slow-traces
        type: latency
        latency: { threshold_ms: 2000 }           # 100% of traces over 2s
      - name: sample-the-rest
        type: probabilistic
        probabilistic: { sampling_percentage: 1 } # 1% of everything else

service:
  pipelines:
    traces:
      receivers:  [otlp]
      processors: [tail_sampling, batch]
      exporters:  [otlp]
```

That config is the entire "scenario" above made real: errors and slow traces kept at 100%, normal traffic at 1%. (Adding `memory_limiter`, `filter`, and `attributes` processors — the rest of the cost toolkit — is in [`middle.md`](middle.md).)

### Dropping a high-cardinality metric label at the source

```yaml
processors:
  # Strip the cardinality-bomb label before it ever reaches the metrics backend.
  attributes/drop-userid:
    actions:
      - key: user_id
        action: delete            # remove user_id from every metric data point

service:
  pipelines:
    metrics:
      receivers:  [otlp]
      processors: [attributes/drop-userid, batch]
      exporters:  [prometheusremotewrite]
```

The same `user_id` is fine — even valuable — as a *trace attribute* or *log field*, where cardinality is cheap. Cost control is often just **moving** data to where it's cheap, not deleting it.

---

## What Telemetry Costs

| Thing | What you pay for | Scales with |
|---|---|---|
| One metric **time series** | storage of every point, forever in retention | **cardinality** (label combinations) |
| One **log line** | transmit + store (× retention) + often index | **volume** (bytes × retention) |
| One **trace** | transmit + store every span | **volume × spans per trace** |
| A **scrape / ingest** | the metered, billed event in most SaaS pricing | number of series / GB / events |
| **Retention** | storage for the whole window | days kept × volume |
| **Indexing** | fast search over logs/traces | bytes indexed |

The headline: **emitting is cheap; keeping is the bill.** A counter you increment a billion times is one series. A log line you write a billion times is a billion lines you store. The difference is *aggregation* — and the cheapest cost lever of all is to aggregate at the source and keep the summary, not the raw stream. (See [`middle.md`](middle.md).)

---

## Best Practices

1. **Never sample away errors, audit/security events, SLO signals, or billing.** This is the one inviolable rule. Tail-sample so these are kept at 100%.
2. **Control cost in the collector, not the code.** Keep the app emitting; decide what to keep centrally so you can change it without a deploy.
3. **Treat every new metric label as a cardinality decision.** If you can't list its possible values on a whiteboard, it's probably a bomb. Identity (user/request IDs, emails, URLs) goes in logs/traces, never metric labels.
4. **Use both head and tail sampling** — head for a raw cost cap, tail to make sure the survivors are the useful ones.
5. **Turn DEBUG off in prod by default** and make log level changeable at runtime, not only at deploy.
6. **Tier your retention.** You rarely need 90 days of full-resolution data; keep recent data hot and downsample older data.
7. **Alert on telemetry spend / cardinality**, not just on the system. A new high-cardinality label should page *you* before it pages your finance team.

---

## Edge Cases & Pitfalls

- **Random sampling drops your errors.** A flat 1% head sample keeps ~1% of errors too. If errors matter (they do), you need tail sampling, not just a lower head rate.
- **Counting from sampled data without adjusting.** If you keep 1% and report the raw kept count as "total requests," you're under-reporting by 100×. Multiply by `1/sample_rate`. (See [`senior.md`](senior.md).)
- **Tail sampling with split traces.** If a trace's spans land on *different* collector instances, none of them sees the whole trace and the tail decision is wrong. Spans of one trace must reach the same collector. (Topology: [`middle.md`](middle.md).)
- **Dropping a label you derive alerts from.** Strip `status` to save cardinality and your error-rate alert goes blind. Know what queries depend on a label before you drop it.
- **DEBUG logging left on in prod.** The single most common logs-cost blowout. One config flag, enormous bill.
- **Sampling configured per-service inconsistently.** Service A keeps a trace, service B drops its half of it → broken, half-empty traces. Sampling decisions must be *consistent* across services. ([`senior.md`](senior.md).)
- **Memory blowout from tail sampling.** Buffering every in-flight trace uses RAM proportional to traffic × decision_wait. Without `memory_limiter`, the collector OOMs under load — exactly when you need it.

---

## Common Mistakes

1. **"Log/trace/measure everything" as a default.** The instinct that produces the runaway bill. Decide what to keep on purpose.
2. **Putting identity (`user_id`, `request_id`, email, full URL) in a metric label.** The #1 cardinality explosion. It belongs in a log or trace attribute.
3. **Using random head sampling and being surprised errors vanished.** Random sampling is blind; it can't preserve rare-but-important traces.
4. **Reporting metrics derived from sampled traces without multiplying by `1/sample_rate`.** Silently wrong numbers.
5. **Fixing the wrong bill** — shortening log retention to cut a metrics-cardinality cost. Match the lever to the driver.
6. **Cutting cost by dropping the signals you actually need** (Goodhart: gaming "reduce telemetry spend" by deleting fidelity). Cross-ref Engineering Metrics & DORA.
7. **Sampling in the application code**, hard-coded, so changing it needs a deploy. Do it in the collector.
8. **No alerting on telemetry cost**, so the first signal is the invoice.

---

## Tricky Points

1. **Head sampling can be cheap *and* consistent — but never *smart*.** It can guarantee the same decision across services (via the `trace_id`), which is great; it can never know whether the trace is interesting, which is its ceiling.
2. **Tail sampling needs the whole trace, which constrains topology.** You can't freely load-balance spans across collectors; a trace's spans must converge on one decision-maker. This is why large setups use a two-tier collector (agent → gateway).
3. **Dropping a label is not always free of meaning.** `http_requests_total` summed without the `status` label can't tell you the error *rate* anymore. Cardinality reduction can quietly destroy a query.
4. **Sampling rate and statistical correctness are linked.** Every count, rate, or percentage you derive from sampled traces must be scaled by `1/sample_rate` to mean what it says. (Worked maths: [`senior.md`](senior.md).)
5. **Exemplars are the cheap bridge.** Instead of keeping expensive traces to explain a metric spike, attach one *exemplar* (a trace pointer) to the cheap metric. You get "show me an example" without paying trace prices for every request.
6. **"Keep everything" can be cheaper than bad sampling if the data is tiny** — don't reflexively sample low-volume, high-value signals. Sampling is for *high-volume* data.

---

## Apply it

1. Choose one small, known input for **Telemetry Cost & Sampling Strategy**.
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

- What problem does Telemetry Cost & Sampling Strategy solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
