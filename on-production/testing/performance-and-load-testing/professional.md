# Performance & Load Testing — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Performance & Load Testing** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Testing](../README.md) → Performance & Load Testing

*The pre-launch load test that everyone forgets to run again is the most common performance-testing anti-pattern in our industry. A professional builds load testing into a continuous practice with SLOs as the contract, owned costs, and a real answer for distributed systems.*

---

## Core Concept 1 — From ritual to practice

The anti-pattern, stated plainly: a team load-tests once, two weeks before launch, on a hastily-built staging environment, hits its number, screenshots the graph, and never runs it again. Three months later the code, the data volume, the dependencies, and the traffic have all changed — and the screenshot is a museum piece.

Performance is not a property you verify once; it is a property that **decays continuously** as the system evolves. Every feature adds work; every data-volume increase slows queries; every new dependency adds tail latency. A practice that tests once cannot see this drift.

The professional reframe: treat performance like correctness. You would never run your unit tests once before launch and call it done — you run them on every change. Performance testing belongs on the same footing, at an appropriate cadence:

- **Per PR:** fast micro-benchmark gates on hot paths.
- **Nightly / per-merge to main:** a full load test against a prod-like env, results trended.
- **Pre-release:** the formal SLO validation, plus stress/spike if risk warrants.
- **Continuously in prod:** synthetic canaries and real-traffic observation (`../testing-in-production/`).

The cultural marker of maturity: nobody can name "the time we load-tested" because it happens all the time, and the dashboard of p99-over-time is on a wall.

---

## Core Concept 2 — SLOs as the pass/fail contract

A load test without an SLO produces numbers; a load test *with* one produces a **verdict the whole org agrees on in advance.** This is the bridge between testing and reliability engineering (`../../engineering-metrics-and-dora/`, the `monitoring-alerting` skill).

Make the SLO the literal pass/fail condition of the test:

```javascript
// k6 thresholds = SLO encoded as the test verdict
export const options = {
  thresholds: {
    'http_req_duration{endpoint:checkout}': ['p(99)<300', 'p(99.9)<800'],
    'http_req_duration{endpoint:browse}':   ['p(99)<150'],
    'http_req_failed': ['rate<0.001'],          // 99.9% availability target
    'checks':          ['rate>0.999'],
  },
};
```

Principles:

- **Per-endpoint SLOs.** Checkout and a health check do not share a latency budget. Tag and threshold separately.
- **Tail SLOs, not averages.** State p99 / p99.9 — the senior lesson institutionalised.
- **Tie to the error budget.** If the load test predicts you will spend the month's error budget at expected peak, that is a release-blocking finding, not a footnote.
- **The same SLO in test and prod.** The threshold that gates the load test should equal the SLO your `monitoring-alerting` dashboards enforce in production. One number, two enforcement points — otherwise the test validates something you don't actually promise.

The SLO turns "is it fast enough?" (subjective, endless) into "does it meet the agreed objective?" (binary, owned).

---

## Core Concept 3 — When to run what

A decision matrix the team can actually follow:

| Trigger | Test type | Environment | Gate? |
|---------|-----------|-------------|-------|
| Every PR | Micro-benchmarks (hot paths) | CI runner (pinned) | Yes — fail on significant regression |
| Merge to main / nightly | Load test at expected peak | Prod-like staging | Soft — trend + alert |
| Before a release | Load + spike (SLO validation) | Prod-like / prod canary | Yes — release gate |
| Before a known surge (sale, launch) | Spike + stress | Prod-like at scale | Yes |
| Quarterly / major arch change | Stress + capacity + scalability | Prod-scale | Findings → capacity plan |
| Weekly (long-running services) | Soak (hours) | Prod-like | Alert on drift |
| Continuously | Synthetic canaries | Production | Alert (not gate) |

The art is matching cost to value: you cannot run a prod-scale 6-hour soak on every PR, and you should not gate a release on a noisy micro-benchmark. Cheap/fast tests run often and gate; expensive/realistic tests run rarely and inform.

---

## Core Concept 4 — Load testing distributed systems

Single-service load testing is the easy case. Real systems are meshes, and that changes the discipline:

- **The bottleneck moves.** Stress the API and you may saturate the *database*, the *message queue*, or a *downstream service* instead — possibly one another team owns. The load test's job expands to *finding which component fails first*, which requires telemetry across all of them on a shared clock.
- **Autoscaling changes the answer.** With autoscaling, the question isn't "what's the ceiling?" but "does capacity arrive *fast enough*?" A spike test must account for **autoscaling lag** — the 60–300 s between load rising and warm capacity serving. During that gap, SLOs can breach even though steady-state capacity is ample. Test the *transient*, not just the plateau.
- **Cascading failures and backpressure.** A saturated downstream can trigger retry storms and thundering herds that bring down healthy upstream services. Load testing distributed systems means watching for these emergent modes (and validating that circuit breakers, rate limits, and bulkheads — the `circuit-breaker-pattern`, `rate-limiting-throttling`, `load-balancing` skills — actually engage under load).
- **Stateful and async paths.** Throughput at the HTTP edge can look fine while a queue silently backs up. Measure end-to-end completion (including async workers), not just the synchronous 200, or you measure *acceptance*, not *processing*.
- **Generator scale.** Producing real distributed-system load needs distributed *generators* — a single box cannot saturate a cluster, and one machine's egress/CPU becomes the bottleneck before the target does. Use k6 Cloud, distributed Locust workers, or many vegeta nodes, and confirm the generators themselves are not the limit.

---

## Core Concept 5 — Capacity planning from load tests

A load test that finds the knee feeds directly into capacity planning (with the `system-design-estimation` skill):

```text
From a capacity test:
  one node sustains 800 req/s at p99 = 250ms (just under SLO)  → per-node capacity
  expected peak = 5,000 req/s
  nodes needed at peak = 5000 / 800 = 6.25 → 7 nodes
  headroom target = 40% (for spikes, failover, deploys)
    → provision 7 / 0.6 ≈ 12 nodes
  also verify: can the SHARED tier (DB, cache, queue) take 5,000 req/s?
    (per-node math fails if a shared dependency saturates first)
```

The two professional cautions: (1) per-node linear extrapolation breaks once a *shared* resource (database, cache, lock) saturates — scalability is not free, which is exactly what a **scalability test** verifies (does adding nodes actually raise throughput, or does the DB cap it?); (2) headroom is non-negotiable — provisioning for exactly the measured peak leaves nothing for spikes, a failed AZ, or a slow deploy. Capacity = measured per-unit throughput ÷ utilisation target, validated against the shared tier.

---

## Core Concept 6 — The economics of load testing

Load testing is not free, and cost shapes the practice — this is a first-class professional concern.

**Where the money goes:**
- **System under test.** A prod-like environment is, by definition, prod-priced. Running it 24/7 for tests is expensive; spin it up on demand.
- **Load generators.** Producing 50k req/s needs real fleet — distributed generators cost compute and egress. Cloud load services bill per virtual-user-hour.
- **Data.** A prod-scale dataset costs storage and time to build/refresh (`../test-data-management/`).
- **Engineer time.** Building and maintaining realistic scenarios is ongoing work.

**Cost-control patterns:**
- **Ephemeral environments** — provision the prod-like stack for the test window, tear it down after. Infrastructure-as-code makes this routine.
- **Right-size the cadence** — expensive tests run rarely (Core Concept 3). Don't run a $200 prod-scale soak on every commit.
- **Scaled-down with extrapolation** — test at 1/10 scale and extrapolate *carefully*, knowing extrapolation breaks at shared-resource saturation. Cheaper, but treat results as estimates.
- **Test in production** — shadow traffic and canaries reuse real infrastructure and real load, sidestepping a separate test fleet (with the risks of `../testing-in-production/`).

The trade-off is always **fidelity vs. cost**: the cheapest test (laptop, tiny data) is worthless; the most faithful (full prod-scale, real data, distributed generators) is expensive. A professional places each test deliberately on that curve based on what decision it informs.

---

## Core Concept 7 — Organising the practice and its data

- **Tests live in version control** next to the code, reviewed like code. A load test is an asset that decays if not maintained.
- **Baselines are versioned artifacts.** Store per-release baselines so you can answer "did p99 regress since 2.3?" Update them deliberately, with a reason in the commit.
- **Results are persisted and trended,** not screenshotted. Pipe k6/Locust output to a time-series store (Prometheus/InfluxDB + Grafana — the `observability-stack`). The p99-over-time chart is the practice's heartbeat.
- **Scenarios are realistic and refreshed.** Derive the request mix and data skew from *production* analytics, and refresh them as traffic evolves. A scenario modelling last year's traffic tests a system that no longer exists.
- **Ownership is explicit.** Someone owns the load-test suite, the staging env, and the SLO definitions. Unowned performance practices rot fastest.

---

## Core Concept 8 — Governance, safety, and culture

Load testing is a *destructive* activity. Governance keeps it from becoming an outage.

- **Never load-test shared/production environments without authorisation and a blast-radius plan.** A stress test *is* a denial-of-service attack against your own infrastructure; treat it with that seriousness.
- **Coordinate.** Announce tests so on-call doesn't mistake a planned stress test for a real incident. Tag synthetic traffic so it's distinguishable in logs and excludable from business metrics.
- **Have a kill switch.** Any load test, especially in or near production, needs an immediate abort and a known-good recovery.
- **Guard the data.** Test data must not be real customer PII; production-like ≠ production data (`../test-data-management/`, the `secrets-management` skill for credentials).
- **Culture:** performance is a shared responsibility, not a pre-launch checkbox owned by one "perf person." The healthiest signal is engineers reading the p99 trend like they read CI status — and a blameless response when a regression slips through, focused on why the gate missed it.

---

## Real-World Examples

- **The museum screenshot.** A fintech load-tested once before launch (10k rows, single node), hit p99 = 90 ms, never re-ran. Eight months later, p99 in prod was 1.4 s at the same traffic — data had grown 200×. Instituting nightly load tests against a prod-volume dataset surfaced regressions within a day of introduction thereafter.
- **Autoscaling lag.** A spike test that only measured the plateau passed; a real flash sale breached SLO for the first 90 s while autoscaling warmed nodes. Re-running the spike test on the *transient* exposed it; pre-warming + faster scaling policies fixed it.
- **The shared-tier ceiling.** Per-node math predicted 7 nodes for peak; the scalability test showed throughput flatlining at 4 nodes — the shared Postgres primary was the real ceiling. Saved the team from over-provisioning app nodes that would have done nothing.
- **The expensive soak.** A team ran a 6-hour prod-scale soak nightly at significant cloud cost. Moving it to weekly + ephemeral environments cut the bill ~85% with no loss of signal, since leaks accrue over days, not commits.

---

## Common Mistakes

- **The one-time pre-launch ritual** — the defining anti-pattern of the level.
- **Per-node extrapolation past shared-resource saturation**, over-provisioning the wrong tier.
- **Testing only the steady plateau**, missing autoscaling-lag SLO breaches.
- **No headroom** — provisioning for exactly the measured peak.
- **Screenshotting results** instead of trending them; no baseline history.
- **Running expensive tests too often** (or faithful tests never) — wrong point on the cost curve.
- **Load-testing prod with no kill switch, no coordination, real PII** — an outage and a compliance incident waiting to happen.
- **Different SLO numbers in test vs. prod** — the test validates a promise you don't make.

---

## Apply it

1. Define the user or business outcome that **Performance & Load Testing** should improve.
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

- Which measurable outcome justifies investing in Performance & Load Testing?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
