# Observability Engineering — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Observability Engineering** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Topic:** [Observability Engineering Roadmap](README.md)
> **Focus:** Observability as an organisational discipline and platform. The OpenTelemetry pipeline at scale — agent vs gateway Collector topology, where tail sampling lives, multi-tenancy and PII governance. Backend architecture and build-vs-buy (Prometheus/Grafana/Tempo/Loki vs Honeycomb vs Datadog). The observability maturity model and cultural adoption (observability-driven development). SLO practice across many teams, cost governance, on-call and incident response enabled by observability, and the Goodhart traps that ruin observability metrics.

---

## Core Concepts

### 1. Observability is a platform, and platforms have customers

Your customers are the engineering teams. The platform's job is to make rich instrumentation *easy* (sane defaults, shared SDK config, auto-instrumentation, golden dashboards) and the wrong thing *hard* (cardinality guardrails, PII redaction by default). Treat it as a product: paved roads, self-service, documentation, and a feedback loop — not a mandate.

### 2. The Collector tier is where org-level policy lives

In a one-service world the Collector is a convenience. At org scale it is the **policy enforcement point**: tail sampling, PII redaction, attribute normalisation, cost controls, backend routing, and multi-tenancy all live in the gateway tier — *centrally*, without redeploying every service. Owning the Collector topology is owning observability governance.

### 3. Build-vs-buy is a capability and cost decision, not just a price

Self-hosting OSS (Prometheus/Grafana/Tempo/Loki) gives control and avoids per-GB SaaS pricing, but you pay in operational toil and you inherit the TSDB cardinality ceiling. SaaS (Honeycomb, Datadog) buys you the wide-event query model or a turnkey platform, but the bill scales with telemetry volume and can become the dominant cost. There is no universally right answer — only a right answer for your scale, team, and cardinality needs.

### 4. Adoption beats architecture

A perfect pipeline feeding a perfect backend is worthless if teams emit thin spans and never query during incidents. The maturity model and ODD culture are not soft extras — they're the difference between an observability *platform* and an observability *capability*.

### 5. SLOs scale only with discipline

One service's SLO is easy. Fifty teams' SLOs become theatre unless you standardise (what's an SLI, how to set targets, the error-budget policy) without centralising (each team owns its SLOs). The goal is a *shared language*, not a central committee approving every threshold.

### 6. Cost is a first-class design constraint

Telemetry volume grows super-linearly with traffic and microservice count. Without governance — sampling, cardinality budgets, retention tiers, attribution back to teams — the bill becomes a crisis and the reflexive fix (turn down sampling) blinds you exactly when you scale. Cost governance is an observability-design problem, not just a finance one (cross-ref [telemetry-cost](../14-telemetry-cost-and-sampling-strategy/README.md)).

### 7. Observability metrics get Goodharted

The moment "every service must have a dashboard" or "MTTR must drop 20%" becomes a target, teams optimise the *metric*, not the *capability*. Professional practice means choosing observability KPIs that resist gaming and watching for the gaming when it happens.

---

## The Observability Platform — A Reference Architecture

A platform is a pipeline with policy, governance, and a product surface around it.

```text
  ┌─ SERVICES (polyglot: Go, Python, Java, Node) ─┐
  │  OTel SDK / auto-instrumentation              │   instrument ONCE (vendor-neutral)
  └───────────────────────┬───────────────────────┘
                          │ OTLP
                          ▼
  ┌─ AGENT COLLECTOR (per-node DaemonSet / sidecar) ─┐
  │  receive · enrich (k8s metadata) · batch         │   first hop, near the workload
  └───────────────────────┬───────────────────────────┘
                          │ OTLP (load-balancing exporter, trace-aware)
                          ▼
  ┌─ GATEWAY COLLECTOR TIER (scaled deployment) ─────────────────────┐
  │  TAIL SAMPLING · PII redaction (OTTL) · attribute normalisation   │   ORG POLICY
  │  span→metrics connector · cost controls · multi-tenant routing    │   lives here
  └──────────┬───────────────────┬───────────────────┬───────────────┘
             ▼                    ▼                   ▼
        TRACES backend       METRICS backend      LOGS backend
        (Tempo / Honeycomb)  (Prometheus/Mimir)   (Loki)
             └─────────── single query/pivot layer (Grafana / SaaS UI) ──────────┘
                          dashboards · SLOs · alerting · ad-hoc exploration
```

Key properties this buys you:

- **Instrument once, govern centrally.** Apps speak OTLP; everything downstream — sampling, redaction, backend choice — changes in the Collector tier without app redeploys.
- **PII never leaves un-redacted.** A redaction stage in the gateway is the chokepoint where you guarantee emails/card numbers/tokens are scrubbed before export, especially to a third-party SaaS.
- **Cost lives in one place.** Sampling and cardinality controls are centralised, so you can tune the bill without touching fifty repos.
- **Backends are swappable.** Re-point an exporter; run two backends in parallel during a migration.

---

## Collector Topology: Agent vs Gateway

The single most important platform-architecture decision. The two roles are usually *both* present in a layered topology.

| | **Agent Collector** | **Gateway Collector** |
|---|---|---|
| Runs as | Sidecar or per-node DaemonSet | Centralised, horizontally-scaled deployment |
| Proximity | Next to the workload | A shared tier |
| Does | Receive, add host/k8s metadata, batch, ship | Tail sampling, redaction, normalisation, routing, span-metrics |
| Why | Offload the app, capture node context | Centralise expensive/global processing & policy |
| Scaling | One per node/pod | Scale out by load |

### The tail-sampling constraint that shapes the whole topology

Tail sampling must see **all spans of a trace** to decide whether to keep it — so all spans of a given trace must reach the **same** gateway instance. You cannot naïvely round-robin spans across gateway replicas, or each replica sees a fragment and the decision is wrong. The solution is a **trace-aware load-balancing exporter** on the agent tier that routes by `trace_id`, plus a two-layer gateway (a routing layer that shards by `trace_id`, then a sampling layer). This constraint is *the* reason gateway Collectors exist as a distinct tier and why tail sampling is a platform concern, not an app one.

```text
   agents ──(load-balancing exporter, hash by trace_id)──► gateway replica N
                                                            (sees the WHOLE trace)
                                                            → correct tail decision
```

### Where each policy lives

- **Agent:** host/k8s resource enrichment, batching, initial OTLP receive. Cheap, local, per-node.
- **Gateway:** tail sampling (needs whole traces), PII redaction (one chokepoint), attribute normalisation (consistent names org-wide), `spanmetrics` connector (RED from spans), multi-tenant routing, and exporter fan-out.

For a small org, a single gateway tier suffices. As trace volume grows, split routing from sampling. This topology is what lets a 200-service org change sampling or add a backend with zero app deploys.

---

## Backends and Build-vs-Buy

The backend determines your *capability ceiling* (can you `group by` arbitrary high-cardinality fields?) and a large fraction of your *cost*.

### The OSS / self-host stack

| Tool | Signal | Notes |
|---|---|---|
| **Prometheus** (or **Mimir/Thanos** for scale/HA) | Metrics | The TSDB standard. Cardinality is the cost/scaling ceiling — high-cardinality labels are forbidden. |
| **Grafana** | Dashboards / query layer | The pane-of-glass over Tempo/Loki/Prometheus; exemplar support links metrics→traces. |
| **Tempo** | Traces | Cheap object-store-backed tracing; pairs with tail sampling in the Collector. |
| **Loki** | Logs | Label-indexed log store; correlate via `trace_id`. |
| **Pyroscope / Parca** | Profiles | Continuous profiling; span-aware linking. |

**Strengths:** control, no per-GB vendor pricing, data stays in-house, no lock-in. **Costs:** real operational toil (you run, scale, and upgrade it), and you inherit the TSDB cardinality ceiling — slicing to one customer needs the trace/log side, not Prometheus.

### The SaaS options

| Vendor | Model | Notes |
|---|---|---|
| **Honeycomb** | Wide-event / columnar | Built around the arbitrarily-wide event; `group by` any high-cardinality field, BubbleUp outlier analysis. The native expression of the senior-level model. |
| **Datadog** | Turnkey all-in-one | Broad, polished, fast to adopt; pricing scales with hosts/volume/custom metrics and can dominate the bill. |
| **Grafana Cloud** | Managed OSS stack | Hosted Prometheus/Tempo/Loki — OSS model without the ops. |
| **New Relic / others** | All-in-one | Similar trade-offs to Datadog. |

### The decision framework

| Choose **build (OSS)** when | Choose **buy (SaaS)** when |
|---|---|
| You have platform/SRE capacity to operate it | Engineering time is scarcer than money |
| Data residency / sovereignty is mandatory | You want capability *now*, not in a quarter |
| Volume is huge and per-GB SaaS pricing is prohibitive | The wide-event query model (Honeycomb) is the goal and you won't build a column store |
| You need deep customisation | You'd rather not run a TSDB at scale |

**The pragmatic reality:** most orgs end up **hybrid** — OTel as the universal instrumentation layer (so the choice is reversible), Prometheus/Grafana for cheap, high-value SLO metrics, and a SaaS (often Honeycomb-style) for high-cardinality trace exploration. Because everything speaks OTLP through the Collector, build-vs-buy becomes a *per-signal*, *reversible* decision rather than a one-way door. **OTel is the hedge that keeps the question open.**

---

## The Observability Maturity Model

A staged view of where an org actually is. Useful for honest assessment and for sequencing investment.

| Level | Name | Characteristic | The telling question |
|---|---|---|---|
| **0** | Reactive | Logs grepped on boxes; alerts on host metrics | "What happened?" answered by SSH-ing in |
| **1** | Monitoring | Dashboards + threshold alerts for known failures | "Is X broken?" — but only X you predicted |
| **2** | Structured | Structured logs, RED metrics, some tracing; signals exist but are siloed | "We have logs, metrics, traces" (uncorrelated) |
| **3** | Correlated | Shared `trace_id` across signals; exemplars; you pivot signal→signal | "From this metric spike I can reach the trace and logs" |
| **4** | Observable | Wide events, high-cardinality ad-hoc queries; SLOs; debug unknown-unknowns with no deploy | "We cornered a novel failure in minutes by slicing on a dimension we never alerted on" |
| **5** | Proactive | Observability drives development; experiments in prod; cost-governed; observability is a paved road | "Instrumentation ships with the feature; we explore prod routinely, not just during incidents" |

Use it diagnostically, not as a vanity ladder. The jump that matters most is **2 → 3 → 4**: from "we have the signals" to "they're correlated" to "we can ask new questions." Many orgs stall at level 2 with three expensive, disconnected pipelines and call it observability.

---

## Cultural Adoption & Observability-Driven Development

Tooling is necessary and insufficient. The cultural shifts:

- **Observability-Driven Development (ODD).** Instrumentation is part of the feature's definition of done, written *with* the code — "what wide-event attributes would I need to debug this in prod?" — not bolted on after the first outage. Reviewers ask for it like they ask for tests.
- **Debug in production, routinely.** Normalise exploring prod telemetry as a daily habit, not a panic move. Engineers who only open the observability tool during incidents never build the fluency to use it well *during* incidents.
- **Watch the ones who instrument richly.** The teams that resolve incidents fast are the ones whose spans are wide and whose attributes match their domain. Make their patterns the paved road.
- **Paved roads over mandates.** Ship shared SDK config, auto-instrumentation, golden dashboards, and SLO templates so the easy path is the rich-instrumentation path. Mandates without ergonomics produce checkbox compliance (level-2 theatre).
- **Blameless incident culture.** Observability and blamelessness reinforce each other: people share what the data shows when they won't be punished for what it reveals (cross-ref [post-mortem-analysis](../10-post-mortem-analysis/README.md)).

The adoption test is behavioural, not architectural: *do engineers reach for the observability tool to answer questions, including outside incidents?* If yes, you have a capability. If they only look at dashboards someone else built, you have shelfware.

---

## SLO Practice at Org Scale

One service's SLO is a senior topic; *fifty teams'* SLOs is a professional one. The failure mode is bureaucracy or theatre. (Mechanics: engineering-metrics-and-dora.)

- **Standardise the *language*, decentralise the *targets*.** Define org-wide what an SLI is (user-perceived, request-level, split success/error), how to express it as a query over wide events, and what an **error-budget policy** is. Let each team own its own SLO numbers and own its budget. Centralising target-setting creates a committee bottleneck; decentralising the *definition* creates incomparable nonsense.
- **SLOs on user journeys, not just services.** "Checkout succeeds" is a journey crossing many services; per-service SLOs can all be green while the journey is broken. Define journey-level SLOs for the things users actually do.
- **The error-budget policy must have teeth.** Pre-agree the consequence of burning the budget (freeze features, shift to reliability work). An SLO with no consequence is a vanity metric.
- **Alert on multi-window, multi-burn-rate** budget consumption, not raw thresholds — page on a fast burn that threatens the budget, ticket on a slow burn. This is the org-scale answer to alert fatigue (see `monitoring-alerting`).
- **Beware SLO inflation.** Teams set 99.99% because it *sounds* responsible, then chronically miss it and the SLO loses all meaning. Set the target at the level users actually need; an SLO you reliably meet *and* that reflects user pain is worth more than an aspirational one you ignore.

---

## Cost Governance

Telemetry is frequently a top-three infrastructure cost and grows faster than traffic (more services × more spans × more attributes). Without governance, the reflex when the bill spikes is to slash sampling — which blinds you precisely as you scale. (Deep dive: [telemetry-cost](../14-telemetry-cost-and-sampling-strategy/README.md).) The governance levers:

| Lever | What it does | Where |
|---|---|---|
| **Tail sampling** | Keep all errors/slow/key-tenants, sample the boring majority | Gateway Collector |
| **Cardinality budgets** | Cap per-team metric label cardinality; alert/drop on breach | Collector + policy |
| **Attribute pruning** | Drop attributes that are never queried (pure cost) | Collector (OTTL) |
| **Retention tiers** | Hot/cheap-cold tiers; keep raw events briefly, aggregates longer | Backend config |
| **Cost attribution** | Tag telemetry by team/service so spend is showback/chargeback | Resource attributes |
| **Metrics vs traces split** | Metrics are cheap aggregates (no sampling); spend the sampling budget on traces | Pipeline design |

The professional stance: **make cost visible and attributable**, so the team generating the spend sees the spend. The most powerful single move is keeping **metrics unsampled and cheap** (they power SLOs) while aggressively tail-sampling traces — full-fidelity "something's wrong" with sampled "here's why." And resist the panic-sampling reflex: the right cut is dropping *boring* data (unqueried attributes, successful-fast-path traces), not blanket-reducing fidelity on the failures you'll need.

---

## On-Call & Incident Response

Observability's payoff is realised in the incident. (Cross-ref [post-mortem-analysis](../10-post-mortem-analysis/README.md); see the `monitoring-alerting` skill for alert design.)

- **Good observability shrinks MTTR by collapsing the investigation loop.** An on-call engineer who can hypothesise → query wide events → narrow → confirm resolves in minutes; one who must add-log-and-redeploy is stuck for hours. The platform's ROI is mostly here.
- **Alerts must be actionable.** Every page should mean "a human must act now" and link to the relevant SLO and a starting query/dashboard. Non-actionable pages are alert fatigue, and fatigue causes missed real incidents — the most dangerous failure mode of all.
- **Runbooks point into the telemetry.** A good runbook is "open *this* SLO, run *this* `group by`, look for *this* pattern" — not prose. Observability turns runbooks from rituals into queries.
- **The incident timeline is reconstructed from telemetry.** Wide events with build/deploy/flag attributes let the post-mortem answer "what changed at 14:02?" precisely. Capturing `build.version` and `deployment` on events is what makes "the deploy did it" a query rather than a guess.
- **Feedback loop:** every incident either confirms the instrumentation was sufficient or names the missing attribute. Add it. Over time, ODD + this loop drive the org up the maturity model.

---

## Goodhart Pitfalls on Observability Metrics

> *Goodhart's Law: when a measure becomes a target, it ceases to be a good measure.*

Observability KPIs are unusually easy to game because the *capability* (answering unknown-unknowns) is hard to measure, so proxies get targeted instead — and proxies get optimised. (The DORA/SPACE discussion in engineering-metrics-and-dora covers the general phenomenon.)

| Targeted metric | How it gets gamed | The real thing it was a proxy for |
|---|---|---|
| **"% of services with a dashboard"** | Auto-generate empty dashboards nobody uses | Can you actually answer questions? |
| **"Instrumentation coverage %"** | Thin auto-spans everywhere, zero business attributes | Wide, query-useful events |
| **MTTR target** | Resolve = "page acked"; or split one incident into many small "fast" ones | Genuinely faster diagnosis |
| **Alert count down** | Silence/raise thresholds until nothing fires (and real incidents are missed) | Less *noise*, not less *signal* |
| **SLO compliance %** | Set lax SLOs; define "valid request" to exclude the failures | User-perceived reliability |
| **# of custom metrics** | Emit thousands of unqueried metrics (and blow the cost) | Useful, queried signals |

Defences: **measure outcomes, not activity** (time-to-corner-a-novel-incident beats dashboard count); **use a basket of metrics** so gaming one shows up in another; **pair every quantitative KPI with qualitative signal** (do engineers say the tooling helps?); and **never tie observability metrics directly to individual performance reviews** — that guarantees gaming. The honest top-level question resists Goodharting because it's expensive to fake: *the last three novel incidents — were they cornered by querying, with no new instrumentation?*

---

## Code Examples

### Gateway Collector — org policy: tail sampling, PII redaction, span→metrics, multi-backend

```yaml
# gateway-collector.yaml  (the org POLICY enforcement point)
receivers:
  otlp: { protocols: { grpc: { endpoint: 0.0.0.0:4317 } } }

processors:
  # 1) Normalise + redact PII before anything leaves the building (one chokepoint).
  transform/redact:
    trace_statements:
      - context: span
        statements:
          - delete_key(attributes, "app.user.email")
          - replace_pattern(attributes["http.url"], "token=[^&]+", "token=REDACTED")
  # 2) Tail sampling — keep what you'll actually need; requires whole traces (see topology).
  tail_sampling:
    decision_wait: 12s
    policies:
      - { name: errors,      type: status_code, status_code: { status_codes: [ERROR] } }
      - { name: slow,        type: latency,     latency: { threshold_ms: 1000 } }
      - { name: key-tenant,  type: string_attribute,
          string_attribute: { key: app.customer.plan, values: [enterprise] } }
      - { name: rest,        type: probabilistic, probabilistic: { sampling_percentage: 3 } }
  batch: {}

connectors:
  # 3) Derive RED metrics from spans — full-fidelity metrics WITHOUT separate instrumentation.
  spanmetrics:
    histogram: { explicit: { buckets: [50ms, 100ms, 300ms, 1s, 3s] } }
    dimensions: [ { name: http.route }, { name: app.customer.plan } ]

exporters:
  otlp/tempo:     { endpoint: tempo:4317,     tls: { insecure: true } }   # sampled traces
  otlphttp/hny:   { endpoint: https://api.honeycomb.io }                  # wide-event explore
  prometheusremotewrite: { endpoint: http://mimir:9009/api/v1/push }      # UNSAMPLED metrics

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [transform/redact, tail_sampling, batch]
      exporters: [otlp/tempo, otlphttp/hny, spanmetrics]   # spanmetrics fans into metrics
    metrics:
      receivers: [spanmetrics]
      processors: [batch]
      exporters: [prometheusremotewrite]                   # metrics are NOT tail-sampled
```

This one file is org-level governance: PII can't leak, fidelity is allocated, RED metrics are free and unsampled, and three backends are fed without a single app redeploy.

### Agent Collector — trace-aware routing to the gateway (the tail-sampling prerequisite)

```yaml
# agent-collector.yaml  (per-node DaemonSet)
receivers:
  otlp: { protocols: { grpc: { endpoint: 0.0.0.0:4317 } } }
processors:
  k8sattributes: {}     # enrich with pod/namespace/node — node context lives near the node
  batch: {}
exporters:
  # Route ALL spans of a trace to the SAME gateway replica, hashing by trace_id,
  # so tail sampling downstream sees whole traces.
  loadbalancing:
    routing_key: traceID
    protocol: { otlp: { tls: { insecure: true } } }
    resolver: { dns: { hostname: otel-gateway-headless } }
service:
  pipelines:
    traces: { receivers: [otlp], processors: [k8sattributes, batch], exporters: [loadbalancing] }
```

### Java — shared SDK config as a paved road (auto-instrument + standard resource attributes)

```java
// Started via the OpenTelemetry Java agent; this config is the org "paved road".
// -javaagent:opentelemetry-javaagent.jar
//   OTEL_SERVICE_NAME=checkout
//   OTEL_RESOURCE_ATTRIBUTES=service.version=4.2.1,deployment.environment=prod,team=payments
//   OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-agent:4317
//   OTEL_TRACES_SAMPLER=parentbased_always_on   // SAMPLE AT THE TAIL in the gateway, not here
//
// Teams add only business attributes; the platform owns the rest.
import io.opentelemetry.api.GlobalOpenTelemetry;
import io.opentelemetry.api.trace.Span;

void onCheckout(Checkout c) {
    Span span = Span.current();                      // auto-created by the agent
    span.setAttribute("app.account.id", c.accountId());   // identity (high-card: fine on a span)
    span.setAttribute("app.customer.plan", c.plan());     // business dimension to group by
    span.setAttribute("app.payment.provider", c.provider());
}
```

The platform ships the agent, the resource attributes (including `team` for cost attribution), and the "sample at the tail, not the head" decision. Teams write only the domain attributes — the paved road that makes rich instrumentation the easy path.

---

## Best Practices

1. **Layer the Collector:** agents for local enrichment/batching, a gateway tier for tail sampling, redaction, normalisation, span-metrics, and routing.
2. **Route by `trace_id`** (load-balancing exporter) so tail sampling sees whole traces — this constraint shapes the whole topology.
3. **Redact PII at one chokepoint** in the gateway, especially before any SaaS export.
4. **Keep metrics unsampled and cheap; tail-sample traces** for fidelity-where-it-matters; SLOs come from the unsampled metrics.
5. **Use OTel as the reversibility hedge** — make build-vs-buy a per-signal, reversible choice.
6. **Ship paved roads:** shared SDK/agent config, golden dashboards, SLO templates, standard resource attributes (incl. `team` for cost attribution).
7. **Standardise the SLI language, decentralise targets**, define journey-level SLOs, and give the error-budget policy real teeth.
8. **Govern cost** with cardinality budgets, attribute pruning, retention tiers, and showback — make spend visible to the team that creates it.
9. **Make every alert actionable** and link it to an SLO + a starting query; ruthlessly cut non-actionable pages.
10. **Measure observability by outcomes** (time-to-corner-a-novel-incident), resist Goodhart, never tie to individual performance.

---

## Edge Cases & Pitfalls

- **Sharded gateways breaking tail sampling.** Round-robining spans across replicas gives each a fragment → wrong decisions. Route by `trace_id`.
- **Tail-sampler memory pressure** from long-lived traces (a 30-minute trace pins memory in the gateway). Cap durations; size the tier; tune `decision_wait`.
- **PII leaking to a SaaS** because redaction was per-service and one service skipped it. Centralise redaction in the gateway.
- **SLO theatre:** aspirational 99.99% targets chronically missed and ignored, or "valid request" defined to exclude the failures. Set targets to real user need.
- **Per-service SLOs all green, the user journey broken.** Add journey-level SLOs.
- **Cost panic → blanket sampling cut** that blinds you as you scale. Cut *boring* data, not failure fidelity; keep metrics unsampled.
- **Cardinality bombs from resource attributes** (`host.name` per pod) inflating metric series. Fine on events; guard as metric labels.
- **Goodharted KPIs:** dashboards/coverage/MTTR targets gamed into meaninglessness. Measure outcomes; basket of metrics; qualitative signal.
- **"Single pane of glass" as a procurement slogan** — buying one tool doesn't create correlation; correlation is shared `trace_id` + exemplars + wiring.

---

## Common Mistakes

1. **Treating observability as a tooling purchase.** A SaaS contract doesn't make you observable; rich instrumentation + correlation + culture do.
2. **No gateway tier**, so tail sampling/redaction/cost control are scattered into apps and can't change without redeploys.
3. **Round-robin span routing** that silently corrupts tail-sampling decisions.
4. **Sampling metrics** (then computing SLOs from them and getting the error rate wrong) — metrics should be unsampled.
5. **Mandating coverage without ergonomics** — checkbox compliance, thin spans, level-2 theatre.
6. **SLOs with no error-budget policy** — vanity numbers with no consequence.
7. **Slashing sampling when the bill spikes** instead of dropping unqueried/boring data — going blind at scale.
8. **Targeting observability KPIs** (dashboard count, MTTR) and getting them gamed; tying them to individual reviews.

---

## Tricky Points

1. **Tail sampling forces topology.** Because the decision needs the whole trace, you *must* route by `trace_id` to a sticky gateway — this is why a gateway tier exists, and why you can't just scale Collectors statelessly for traces.
2. **Metrics and traces want opposite sampling.** Metrics: unsampled (cheap aggregates, power SLOs). Traces: sampled (per-event, expensive). Designing them the same way breaks either cost or SLO accuracy.
3. **OTel makes build-vs-buy reversible and per-signal** — the strategic value of OTel is as much about *keeping the question open* as about instrumentation.
4. **The maturity leap is correlation, not coverage.** You can have 100% of services emitting all three pillars and still be at level 2 if they share no identity.
5. **Cost governance and visibility blindness trade off.** The cheapest pipeline is the one that records nothing; the value is in keeping the *right* fidelity, not minimising volume.
6. **Goodhart hits observability harder than most domains** because the real capability is hard to measure, so easy proxies get targeted and gamed.
7. **PII redaction belongs in the gateway, not the app** — one chokepoint you can audit, versus N services any one of which can leak.

---

## Apply it

1. Define the user or business outcome that **Observability Engineering** should improve.
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

- Which measurable outcome justifies investing in Observability Engineering?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
