# SRE and Reliability — Professional

Google formalized the error-budget model: reliability work and feature velocity trade against one shared, spendable budget instead of being negotiated ad hoc. Two ideas from that model matter most at platform scale.

## Multi-window, multi-burn-rate alerting

A single "SLO burned X% in Y minutes" alert either fires too late for fast, severe burns or too often for slow, tolerable ones. Use **multiple windows** simultaneously:

```text
Fast burn:  2% of 30-day budget consumed in 1 hour  -> page immediately (severe, ongoing incident)
Slow burn:  5% of 30-day budget consumed in 6 hours -> ticket, investigate within a day (real but not acute)
```

A fast-burn alert with no slow-burn counterpart misses a chronic, low-grade problem that will exhaust the budget by month's end without ever looking urgent on any single day.

## Govern SLOs across a shared platform

At platform scale, the dominant failures aren't in any one service — they're in inconsistency across many:

- **Inconsistent SLI definitions.** If "availability" means "returned any response" for one team and "returned a correct response within budget" for another, cross-team SLO comparisons and shared dashboards are meaningless. Standardize SLI definitions centrally; let each team set its own SLO target against that shared definition.
- **Shared-platform ownership.** A platform team's SLO is downstream of every team building on it — govern who can consume how much of the platform's own error budget, the same way capacity is governed.
- **Capacity coupling.** Teams sharing infrastructure (a database cluster, a message broker) can burn each other's error budget through noisy-neighbor effects that no single team's own telemetry reveals — track resource contention at the shared-infrastructure level, not just per-service.

## Design the observability platform, not just individual services' telemetry

| Layer | What it standardizes | Key constraint at scale |
|---|---|---|
| **OpenTelemetry** | Traces, metrics, logs, context propagation, semantic conventions | The standard solves instrumentation consistency; collectors and backends still need capacity and multi-tenancy design |
| **Prometheus-style metrics** | A dimensional (labeled) query model | Powerful for ad hoc queries; high-cardinality labels multiply the number of time series and can overwhelm storage |
| **eBPF** | Low-overhead kernel and user-space observation without redeploying | Requires verifier, privilege, and symbolization handling — not casually available in a multi-tenant cluster |
| **Continuous profiling** (e.g., Parca, Pyroscope-style aggregation) | Always-on CPU/memory profiling across a fleet | Only affordable through profile aggregation; naive always-on profiling at fleet scale is a cost and storage problem |

## What dominates at 10x and 100x scale

- **At 10x:** cardinality and ingestion cost start to dominate the observability budget — a metric label that was fine at 100 services multiplies badly at 1,000.
- **At 100x:** tail-sampling buffer capacity, collector backpressure, tenant isolation, retention tiers, and query latency become architecture decisions in their own right, not configuration tweaks.

Track platform health directly: dropped telemetry rate, collector queue depth, ingestion bytes/sec, active time-series count, trace completeness, profile coverage, and cost per service — a platform with silently dropped telemetry is worse than one with slightly less telemetry that's honestly reported.

## Design and operations checklist

1. Begin from operational questions and SLOs — instrument to answer questions you actually have, not to maximize coverage.
2. Standardize context and semantic fields (trace ID, tenant ID, deployment version) across every team, so signals join cleanly.
3. Bound cardinality, payload size, retention, and access on every signal type before it ships, not after a cost or privacy incident.
4. Preserve enough healthy-traffic telemetry for comparison — sampling only failures removes the baseline needed to explain what "normal" looked like.
5. Test collector and backend failure behavior deliberately — telemetry infrastructure that silently drops data under its own load hides the very incidents it exists to catch.
6. Separate audit, diagnostic, and product-analytics data — different retention, access, and compliance requirements, even when the underlying event looks similar.
7. Make incident learning change something concrete — a runbook, an alert threshold, a piece of telemetry that didn't exist before — not just a document nobody revisits.

```text
QUESTION -> SIGNAL -> CONTEXT -> PIPELINE -> STORAGE -> QUERY -> DECISION
          quality + cost + privacy + resilience + ownership, at every stage
```

## Fund reliability across products

Error budgets only work as a governance tool if risk acceptance and funding are explicit:

- Assign **risk-acceptance authority** — who can decide "we'll ship this feature despite a thin error budget" — and make that decision visible, not implicit in a release going out.
- Fund reliability work **proportionally to the platform's blast radius**, not just to the team that happens to notice the problem first — a shared-dependency fix that benefits ten teams is chronically underfunded if only one team's backlog owns it.
- Watch for a budget being **gamed**: redefining an SLI to exclude the traffic that's actually failing, or shifting failures into a category that isn't measured, both make the budget look healthy while the user experience doesn't improve.

## Test yourself

1. Design multi-window burn-rate alerting for a service with a 99.9% monthly SLO — what are your fast and slow thresholds?
2. How can a shared platform's teams burn each other's error budget without it showing up in any single team's own telemetry?
3. Which specific costs dominate an observability platform at 10x scale versus 100x scale?
4. How would you detect that an SLO is being gamed rather than genuinely improved?
5. How do you fund a reliability fix that benefits many teams but is owned by none of them?

## Further reading

- Google, *Site Reliability Engineering*.
- Google, *The Site Reliability Workbook*.
- Richard Cook, "How Complex Systems Fail."
- OpenTelemetry specifications and semantic conventions.
- Prometheus documentation on data models and cardinality.
- Brendan Gregg, *Systems Performance* and *BPF Performance Tools*.
