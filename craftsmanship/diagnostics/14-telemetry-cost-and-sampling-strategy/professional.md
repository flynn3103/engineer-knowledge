# Telemetry Cost & Sampling Strategy — Professional (Staff / Principal) Level

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Telemetry Cost & Sampling Strategy — Professional (Staff / Principal) Level** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Topic:** [Telemetry Cost & Sampling Strategy Roadmap](README.md)
> **Focus:** Telemetry cost as an **org-wide governed budget** — fidelity is a product decision, not a default; spend is allocated to teams via showback/chargeback; cardinality and sampling are policy-as-code reviewed in CI and shipped via GitOps; the bill is meta-monitored like a production signal; and every cost/fidelity trade-off is made *explicitly* with finance, product, and SRE — never by an engineer deleting the signal that fails the KPI.

---

## Core Concepts

### 1. Fidelity is a product decision, made explicitly, with an owner and a price

The most common organizational failure is that nobody *decided* the org keeps 30-day full-resolution traces — it's just the default the first team set, inherited forty teams later as an unowned, unpriced commitment. At professional level, every fidelity level is a deliberate trade with a name and a number attached: "we keep 30 days full-resolution for $X/year, or 7 days plus tail-sampled for $Y, and product/SRE/finance chose the former because incident forensics need it." Fidelity is a feature of the system with a cost, not a setting.

### 2. A shared bill that nobody is allocated is a commons that will be over-grazed

If telemetry spend lives on one central platform line item, every team's rational move is to instrument maximally — their benefit is private, the cost is socialized. The only durable fix is to **allocate**: make each team see (showback) and ideally pay (chargeback) for its own consumption. The instant a team's GB or series budget is *theirs*, behavior changes — a label that was "free" becomes "comes out of my budget."

### 3. The SDK and wiki cannot govern an org; policy-as-code and CI can

Senior level enforced cardinality in a View or a `metric_relabel_config`. Professional level recognizes that forty teams won't all read the wiki, so the enforcement must be **structural**: allow-lists and sampling rules are version-controlled, reviewed in code review, tested in CI, and rolled out via GitOps. The cheap, correct thing must be the *default and the only thing that merges* — anything else degrades to "we hope everyone is careful," which at org scale means "we don't govern this."

### 4. The telemetry bill is a production signal — meta-monitor it

A bad deploy that flips `DEBUG` on or adds a `user_id` label is detectable *in the telemetry footprint within minutes* — ingest rate spikes, series count jumps, a team's cost-per-hour anomaly fires. You should learn about a cost regression from your own alert during the deploy window, never from the vendor's invoice four weeks later. Meta-monitoring turns cost from a lagging financial metric into a leading operational one.

### 5. Cost serves the observability strategy, never the reverse

Cost discipline exists to make the observability strategy *affordable and sustainable* — it is downstream of "what questions must we be able to answer." If a cost initiative makes a critical question unanswerable, the initiative is wrong, full stop. **You never sample the SLO signal to save money.** Cost is a constraint you optimize within, not the objective function. The objective is answerable questions per dollar, and the floor on "answerable questions" is set by the SLO and incident-forensics needs, not by the budget.

### 6. A cost KPI without a fidelity counter-metric corrupts the thing it measures

"Reduce telemetry spend by 40%" is a Goodhart trap: the easiest way to hit it is to delete the signals you most need. A cost target is only safe when paired with a coverage/fidelity counter-metric — "spend down 40% *and* SLO-signal coverage unchanged, error-trace retention unchanged, MTTR not regressed." Pair every cost number with the fidelity it must not trade away. (Cross-ref Engineering Metrics & DORA.)

### 7. Pricing models are behavioral incentives — each punishes a different sin

Per-host, per-GB, per-series, per-custom-metric, per-event: each pricing model rewards and punishes a *different* engineering behavior. Per-host ignores cardinality (so teams explode it freely); per-custom-metric punishes every tag value; per-GB punishes verbose logs; per-event punishes high span counts. You must know *which* model bills your org and design the org's defaults to its incentive gradient — optimizing series count on a per-host plan is wasted effort; ignoring tag values on Datadog is a budget breach.

---

## Designing an Org Telemetry-Cost Strategy

A telemetry-cost strategy is a *document and a system*, not a one-off cleanup. It answers four questions, and each answer has an owner.

| Question | What it produces | Owner |
|----------|------------------|-------|
| **What must we be able to answer?** | The fidelity floor: SLO signals, error traces, audit/billing — kept at 100%, never traded | SRE + product + security |
| **What can it cost?** | A fleet budget (series / GB / events / $) with headroom reserved | Platform + finance |
| **How is the budget allocated?** | Per-team / per-service caps by tier (Tier-1 API ≠ cron worker) | Platform, ratified with teams |
| **How is it enforced and observed?** | Policy-as-code + CI + GitOps + meta-monitoring + showback/chargeback | Platform owns the mechanism; teams own their allocation |

The principle that anchors the whole document: **fidelity is a first-class, priced product decision, and cost is an SLO-adjacent number** — tracked, budgeted, alerted, and reviewed on the same cadence as reliability, not as an afterthought finance raises once a quarter. Treat "cost per million requests observed" the way you treat an SLO: a target with a budget and an owner.

The deliverable is concrete: a one-page strategy that (1) lists the fidelity floor explicitly, (2) states the fleet budget and the per-tier allocation, (3) names the enforcement mechanism, and (4) names who decides when a trade-off must be made. Without (4), every cost decision becomes an ad-hoc escalation; with it, the answer is "the observability guild ratified the 7-day-warm / 90-day-cold tier in Q2, here's the doc."

---

## Budgets, Chargeback & Showback

The single highest-leverage governance move is to **stop telemetry being free at the point of use.** As long as a team's instrumentation draws on a central bill it never sees, no amount of best-practice evangelism will hold. The ladder has three rungs, and you climb it in order:

1. **Visibility (showback).** Every team gets a dashboard: its active series, GB ingested, events, and the *dollar* equivalent, trended. No billing yet. Showback alone changes behavior — most teams have *no idea* they are the top series producer until they see it. Start here; it's low-friction and politically cheap.
2. **Budget (allocation).** Each team gets a cap, set by tier. The cap is a number it owns and can plan against. Crossing 80% pages the team; crossing 100% triggers the governance loop (below). The budget makes telemetry a resource the team manages, like CPU quota.
3. **Chargeback (billing).** The team's consumption is billed to its own cost center. This is the strongest incentive — now a wasteful label is a line item on *their* budget — but it's the most organizationally expensive to introduce, so most orgs run showback + budgets for a year before charging back.

### Why a per-team budget changes behavior where a wiki never could

A wiki says "be careful with cardinality." A budget says "you have 200k series; you're at 187k; the `tenant_id` label you're about to add will push you over and the merge will fail CI." The first is advice; the second is a constraint with teeth that the team feels at *their* desk, in *their* sprint, against *their* number. This is the same mechanism that makes the `caching-strategies` discipline work — a cache hit-rate target a team owns drives better behavior than a general exhortation to "cache more." Allocation converts a shared, invisible, ignorable cost into a private, visible, actionable one.

### The tragedy-of-the-commons framing, made concrete

```text
   SHARED BILL (ungoverned)                 ALLOCATED BILL (governed)
   ────────────────────────                 ─────────────────────────
   Team A adds user_id label  ─┐            Team A adds user_id label
   Team B turns on DEBUG       ─┼─► one      → CI shows +400k series, BLOCKS merge
   Team C ships 40-span traces ─┘  central   Team B turns on DEBUG
                                   bill         → showback flags +2TB/day on B's budget
   nobody feels the marginal cost            Team C ships 40-span traces
   → bill grows → VP mandates blunt cut         → C's per-event budget alert fires
   → engineers delete needed signal          → each cost felt by its owner, at source
```

The chargeback math is not punitive; it is *informative*. The goal is not to make teams pay — it is to put the marginal cost of a telemetry decision in front of the person making it, at the moment they make it.

---

## Cardinality Governance Program

Cardinality is the cost driver that explodes silently and centrally — one team's `user_id` label can consume the *whole org's* TSDB headroom. Governing it org-wide is a program with named ownership, not a one-time relabel rule.

### The program's six components

| Component | What it is | Where it lives |
|-----------|------------|----------------|
| **Org allow-lists** | The blessed attribute keys per standard instrument (`http.request.method`, `http.route`, …); anything else is dropped | Shared instrumentation library + collector policy |
| **Cardinality review in code review** | A reviewer checklist / PR template item: "does this PR add a metric label? is its value set bounded?" | Code review culture + PR template |
| **CI cardinality check** | A test that scrapes the service in CI, counts distinct series, and **fails the build** on a new high-cardinality attribute | CI pipeline |
| **`metric_relabel_configs` as policy** | The drop/keep rules expressed as version-controlled, reviewed config — the enforcement backstop | GitOps repo |
| **Per-service cardinality budget** | A series cap per service, by tier, enforced in the SDK View / collector | The strategy doc + collector config |
| **Automated new-series detection** | A meta-monitor alerting on `rate(series_created)` jumps and on overflow points, attributing the spike to a service | Meta-monitoring |

### Who owns it (the part orgs forget)

Cardinality governance dies without a named owner. The durable pattern is a **platform/observability team owns the mechanism** (the library, the CI check, the collector policy, the meta-monitor) and **each service team owns its allocation** (staying under its cap, justifying new labels). A cross-team **observability guild** ratifies the allow-list and arbitrates exceptions. "Everyone owns it" means no one does — the bomb ships, and the 3 a.m. TSDB OOM is the first time anyone notices.

### CI as the structural backstop

The wiki catches nothing; code review catches some; CI catches the rest. A CI check that boots the service, scrapes `/metrics`, and asserts "no instrument exceeds N distinct series in this synthetic soak" turns "please be careful" into "the build is red until you bound that label." This is the `monitoring-alerting` discipline applied *to your own pipeline at build time* — the cheapest place to catch a cardinality bomb is before it ever runs in prod.

---

## Sampling Policy as Code

At senior level the collector config was a file you edited and reviewed. At professional level it is a **governed artifact**: version-controlled, peer-reviewed, tested, and rolled out by GitOps — because the config *is* the org's policy for what telemetry is kept versus dropped, and changing it changes the org's fidelity and bill.

### What "policy as code" buys you

- **Auditability:** "why did we stop keeping 100% of `/checkout` errors?" is answered by `git blame`, not a Slack archaeology dig. Every fidelity change has an author, a reviewer, and a date.
- **Review:** a PR that *lowers* a keep-rate on the SLO signal gets caught in review — a wiki edit would not. The reviewer is the guardrail.
- **Testability:** you can unit-test a sampling policy (feed synthetic traces, assert errors survive, assert the rate is right) in CI before it touches prod. The `senior.md` consistency guarantee becomes a *test*, not a hope.
- **Safe rollout:** GitOps applies the change progressively (canary collector, then fleet), with the same rollback you use for app deploys. A bad sampling change is reverted by reverting a commit.

### The structure that scales to an org

```text
   observability-policy/                 ← one GitOps repo, the source of truth
   ├── base/
   │   ├── sampling.yaml                 ← org defaults: keep all errors, all SLO traffic, 1% rest
   │   ├── cardinality-allowlist.yaml    ← the blessed attribute keys
   │   └── retention-tiers.yaml          ← hot/warm/cold + downsampling rules
   ├── overlays/
   │   ├── team-checkout/                ← per-team OVERRIDES (reviewed by the team + platform)
   │   │   └── sampling.yaml             ← e.g. keep p99-tail at 10% for a launch
   │   └── team-search/
   │       └── sampling.yaml
   └── tests/
       └── sampling_test.go              ← assert errors survive, rates correct, floor intact
```

Per-route and per-team **overrides** are first-class: the checkout team raises its tail-sample rate for a launch week via a reviewed overlay PR, scoped to its routes, with an expiry. The base policy guarantees the org floor (errors, SLO traffic never sampled away); overlays let teams tune within it. **A change ships exactly the way a code change ships** — branch, PR, review, CI, canary, rollout, rollback — which is the whole point: fidelity decisions get the same rigor as code, because they *are* code.

---

## The Build-vs-Buy Cost Model

The most consequential telemetry-cost decision an org makes is build-vs-buy, and it is consistently mis-modeled because teams compare the SaaS invoice to the *hardware* of self-hosting and forget the *engineering time*.

### The honest TCO comparison

| Cost dimension | Self-hosted (Prometheus/Mimir/Loki/Tempo + OTel Collector) | SaaS (Datadog / Honeycomb / Grafana Cloud / New Relic) |
|----------------|------------------------------------------------------------|--------------------------------------------------------|
| **Infrastructure** | Your cloud bill: compute, object storage, network | Bundled into the per-unit price |
| **Engineering time** | **The hidden majority cost** — on-call for the observability stack, upgrades, scaling Mimir, debugging Loki, capacity planning | Near-zero ops; you pay for it in the margin |
| **Marginal cost of more data** | Low (your storage is cheap) — favors high fidelity | High (per-GB / per-series / per-host) — favors discipline |
| **Predictability** | Hardware is predictable; engineering toil is not | Predictable *until* a cardinality spike hits overage |
| **Time-to-value** | Weeks to months to stand up well | Days |
| **Lock-in** | Low (OTLP, PromQL portable) | High (proprietary query, dashboards, agents) |

### When each wins

- **SaaS wins** for small-to-mid orgs, teams without a platform group, and anyone whose engineering time is more valuable spent on product than on running Mimir. The per-unit price buys you *not having an observability on-call rotation.*
- **Self-hosting wins** at large scale where the SaaS per-unit bill exceeds the fully-loaded cost of a small platform team running the stack — typically once telemetry volume is large enough that the SaaS margin alone funds the engineers. The crossover is real money, and the *marginal* cost of fidelity is far lower self-hosted, which is why high-volume orgs often keep more data than they could afford on SaaS.
- **The trap in both directions:** modeling self-hosting as "just the hardware" (ignoring the team it needs) makes it look artificially cheap; modeling SaaS as "the list price" (ignoring the discipline overage forces) makes it look artificially expensive. Model the *fully-loaded* cost, including engineer salaries, on both sides. The `observability-stack` skill is the practitioner reference for the components on the self-hosted side of this table.

---

## Vendor Pricing Traps

Every observability vendor's pricing model is an incentive structure, and each one **punishes a different behavior**. Choosing a vendor without modeling your *own* usage against its pricing axis is how orgs sign a contract that bills them for exactly the thing they do most.

| Pricing model | Bills you by | Punishes | The trap |
|---------------|--------------|----------|----------|
| **Per-host** | Number of monitored hosts | Nothing about data — so teams explode cardinality "for free"… until you migrate to per-series and the bill 10×'s | Lulls you into ungoverned cardinality; the reckoning comes at renewal or migration |
| **Per-GB** | Bytes ingested | Verbose logs, fat JSON fields, high log levels | DEBUG-in-prod and structured-log bloat hit hardest |
| **Per-series** | Active time series | Cardinality | The classic `user_id`-label blowout is a direct line item |
| **Per-custom-metric** (Datadog) | Unique metric-name × **tag-set** | **Every distinct tag value** — including ones you never query | The headline trap: a single high-cardinality tag mints thousands of billed custom metrics silently |
| **Per-event** (Honeycomb-style) | Events / spans ingested | High span counts per trace, 100% sampling | Deep traces at high rps without sampling are the cost |

### Ingest vs indexed vs retained — three bills hiding in one

A vendor may price **ingest** (data sent), **indexed** (data made searchable), and **retained** (data stored over time) *separately*. The trap: you optimize ingest, congratulate yourself, and discover indexing was the real cost — or you cut retention and find ingest was 90% of the bill. Decompose the invoice into these three before optimizing, or you'll pull the wrong lever (the [`junior.md`](junior.md) "fix the wrong bill" mistake, now at contract scale).

### Commit and overage cliffs

A committed-spend contract trades a discount for a floor; above the commit, the **overage rate is often 2–5× the committed rate.** A cardinality spike that pushes you over the commit doesn't cost the committed price — it costs the punitive one. **Model the cliff before signing:** plot your projected usage against the commit line *with* a realistic spike, and ask "what does one bad deploy cost us at the overage rate?" The answer should set how aggressively you meta-monitor (below).

### How to model the bill before you sign

```text
   1. Pull 90 days of your OWN usage in the vendor's billing unit (series? GB? events? custom metrics?).
   2. Project growth (traffic × instrumentation roadmap) over the contract term.
   3. Add a realistic worst-case spike (a known-bad deploy pattern) → test the overage cliff.
   4. Price it at LIST, then at the negotiated commit + overage.
   5. Compare against the self-host TCO (incl. the team). Decide on cost-per-fidelity, not sticker.
```

Never sign on the demo dataset's pricing. Sign on *your* data modeled in *their* unit, with the overage cliff stress-tested.

---

## Alerting on Telemetry-Spend Anomalies

Treat the telemetry bill the way you treat any production signal: instrument it, set SLO-style thresholds, and **alert** — so a cost regression pages you during the deploy window, not via the invoice. This is meta-monitoring, and it is the difference between catching a bad deploy by its telemetry footprint in ten minutes and discovering it four weeks later as a $30k surprise.

### What to alert on

| Signal | Alert | Why it's leading, not lagging |
|--------|-------|-------------------------------|
| **Cardinality jump** | `rate(series_created[1h])` spikes, or an overflow point appears | A new high-cardinality label is detectable minutes after deploy |
| **Ingest-rate spike** | GB/min or events/min jumps above baseline for a service | DEBUG flipped on, or a chatty new code path |
| **Cost-per-team anomaly** | A team's projected daily spend deviates from its trend | Attributes the spike to an owner immediately |
| **Approaching commit/budget** | Run-rate projects to exceed the monthly commit or a team cap | Catches the overage cliff *before* you hit it |
| **Floor erosion** | Error-trace keep-rate or SLO-signal coverage drops | A sampling change quietly cut a signal you must keep |

### The principle: catch the footprint before the invoice

A bad deploy that adds a `user_id` label has a *telemetry footprint* — series count climbs immediately, before any cost has accrued. If your meta-monitor fires on `rate(series_created)` within the deploy's canary window, you roll back before the cardinality is even fully minted. The invoice is the *worst* possible detector: it's monthly, aggregated, and arrives after the damage is irreversible. Meta-monitoring (the `monitoring-alerting` discipline pointed at your own pipeline) makes cost a real-time operational signal. The floor-erosion alert is the safety net for [Goodhart Risk](#goodhart-risk): if someone games "reduce cost" by cutting a needed signal, the coverage alert fires.

---

## Making Cost-vs-Fidelity Trade-offs With Stakeholders

The defining professional skill is not finding the cheapest config — it's **framing the trade-off so the right people own the decision.** Engineers should not unilaterally decide the org keeps 7 days of traces instead of 30; that's a product, finance, and SRE decision, and your job is to make it *decidable* by laying out the options with their prices and their risks.

### Frame the trade as priced options, not a recommendation

> "We can keep **30-day full-resolution traces for $X/year**, or **7-day full-resolution + tail-sampled beyond that for $Y/year** (a $Z saving). The 7-day option means incidents older than a week are reconstructed from sampled traces and logs, not full fidelity. Forensics for slow-burn issues (data corruption found weeks later) gets harder. SRE, product, finance: which risk/cost point do we own?"

That framing does three things a bare recommendation can't: it puts a *number* on each option, it names the *risk* of the cheaper one explicitly, and it hands the decision to the people accountable for the risk. You are the one who can compute X, Y, Z and articulate the forensic gap; you are *not* the one who should decide the org's tolerance for it.

### Get the right owners in the room

- **SRE/on-call** owns the incident-forensics risk — they live with reduced fidelity at 3 a.m.
- **Product** owns the customer-impact risk and often the budget pressure.
- **Finance** owns the dollar and the contract cliff.
- **Security/compliance** owns the audit-retention floor (which may be *legally* non-negotiable).

### Document what was traded away

Every trade-off produces an artifact: a short ADR (architecture decision record) stating *what fidelity was reduced, to save how much, accepting what risk, decided by whom, on what date.* Six months later when an incident hits the gap, the answer is "we knowingly traded 30→7 day trace retention in Q2 for $Z, here's the doc and the sign-off" — not "who decided this and why can't I debug last month's outage?" The undocumented trade-off is the one that becomes a blame search during the next incident.

---

## Goodhart Risk

> *"When a measure becomes a target, it ceases to be a good measure."*

A "reduce telemetry cost by 40%" KPI is one of the purest Goodhart traps in engineering, because the **cheapest way to hit it is to delete the signals you most need.** Drop error-trace retention, sample away the SLO signal, turn off the debug logs that explain outages — the cost number drops beautifully, and the org is now blind precisely where it can least afford to be. The KPI was satisfied; the system it measured was corrupted.

### How a cost KPI corrupts fidelity

The mechanism is incentive misalignment: the engineer is rewarded for the cost number and not penalized (until the next incident) for the fidelity loss, because fidelity loss is *invisible until you need it.* You don't notice the missing error trace until 3 a.m. during the outage — long after the KPI was banked and the quarter closed. Cost is immediate and measured; fidelity is latent and unmeasured. Goodhart thrives in exactly that asymmetry.

### The fix: pair the cost KPI with a fidelity counter-metric

Never ship a cost target alone. Pair it:

- "Spend down 40% **and** SLO-signal coverage = 100% (unchanged)."
- "Spend down 40% **and** error-trace keep-rate = 100% (unchanged)."
- "Spend down 40% **and** MTTR not regressed (the real downstream test)."

The counter-metric makes the gaming move *fail its own KPI* — you can't hit "cost down, coverage flat" by deleting coverage. This is the standard Goodhart antidote (pair the optimized metric with the quality it must not trade), covered in depth at Engineering Metrics & DORA, which is the canonical treatment of metric gaming and SLO design and worth reading in full before you set any telemetry-cost target.

---

## Relationship to Observability Strategy & SLOs

Cost discipline is a **servant of the observability strategy, never its master.** The strategy starts from a question — "what must we be able to answer when the system misbehaves?" — and cost is the constraint you optimize *within* while keeping every must-answer question answerable. Invert that order and you get the failure mode where the budget dictates blindness.

### Cost is downstream of "what questions must we answer"

The decision sequence is fixed: (1) define the questions the org must answer (SLO breaches, incident forensics, capacity, security audit); (2) define the signals that answer them (the fidelity floor); (3) *then* minimize cost subject to keeping those signals at 100%. Cost optimization that touches step 2 is out of bounds — you optimize step 3 only. The `observability-stack` skill describes how to build the system that answers those questions; this page is about funding it sustainably without compromising the answers.

### Never sample the SLO signal

This is the inviolable rule, restated at org scale: the signal your error budget is computed from is **sacred.** Sample it and your SLO becomes a guess, your error budget becomes fiction, and your entire reliability program — built on those numbers — runs on corrupted data. The SLO signal sits permanently on the fidelity floor, exempt from every cost initiative, and your sampling policy-as-code must *test* that it survives every policy change. SLO design and error budgets are covered at Engineering Metrics & DORA; the cost-side takeaway is simply: cost discipline stops at the SLO signal's edge.

---

## Code Examples

### Gateway-tier collector: tail sampling + memory_limiter + per-tenant routing

```yaml
# gateway-collector.yaml — the org's central choke point. Version-controlled, GitOps-rolled.
receivers:
  otlp:
    protocols: { grpc: { endpoint: 0.0.0.0:4317 } }

processors:
  # ALWAYS first: shed load before OOM. Tail sampling buffers in-flight traces → RAM risk.
  memory_limiter:
    check_interval: 1s
    limit_percentage: 80
    spike_limit_percentage: 20

  # Org-floor sampling policy. Errors and SLO traffic NEVER sampled away.
  tail_sampling:
    decision_wait: 10s
    num_traces: 200000
    policies:
      - name: floor-keep-all-errors
        type: status_code
        status_code: { status_codes: [ERROR] }
      - name: floor-keep-slo-routes        # the SLO signal — sacred, 100%
        type: string_attribute
        string_attribute: { key: http.route, values: [/checkout, /pay], enabled_regex_matching: false }
      - name: keep-slow
        type: latency
        latency: { threshold_ms: 2000 }
      - name: sample-the-rest
        type: probabilistic
        probabilistic: { sampling_percentage: 1 }

  # Per-tenant routing: attribute the spend to a team for showback/chargeback.
  resource/tag-team:
    attributes:
      - { key: cost.team, from_attribute: service.namespace, action: insert }

exporters:
  otlp/mimir:       { endpoint: mimir-gateway:4317 }
  otlp/tempo:       { endpoint: tempo-gateway:4317 }

service:
  pipelines:
    traces:
      receivers:  [otlp]
      processors: [memory_limiter, tail_sampling, resource/tag-team]
      exporters:  [otlp/tempo]
```

### Policy-as-code / GitOps structure (a reviewed overlay PR)

```yaml
# overlays/team-checkout/sampling.yaml — a TEAM OVERRIDE, reviewed by team + platform.
# Scoped, time-boxed: raise tail-sample rate for the launch week, then expires.
extends: base/sampling.yaml          # inherits the org floor — cannot override errors/SLO keep
override:
  policies:
    - name: launch-week-tail
      type: probabilistic
      probabilistic: { sampling_percentage: 10 }   # 1% → 10% for /checkout during launch
      expires: 2026-07-01                            # CI fails the build after this date
  scope: { http.route: [/checkout] }
```

### `metric_relabel_configs` enforcing a cardinality allow-list policy

```yaml
# base/cardinality-allowlist.yaml — the blessed keys. Allow-list, NOT deny-list (fails closed).
metric_relabel_configs:
  # Keep ONLY the approved labels on the hot HTTP histogram; drop everything else.
  - source_labels: [__name__]
    regex: 'http_server_request_duration_seconds.*'
    action: keep
  - regex: '^(method|route|status_class|service|env)$'   # the allow-list
    action: labelkeep                                     # any label not listed is dropped
  # Hard drop of known cardinality bombs anywhere they appear.
  - regex: '(user_id|request_id|session_id|email|full_url)'
    action: labeldrop
```

### Recording rule + retention tiers (hot/warm/cold) for Mimir/Thanos

```yaml
# retention-tiers.yaml — pre-aggregate at write, downsample over time.
# Recording rule: collapse high-res raw into a cheap rolled-up series for long retention.
groups:
  - name: cost-rollups
    interval: 1m
    rules:
      - record: http:request_rate5m:by_route        # cheap, queryable for 90d
        expr: sum by (route, service) (rate(http_server_request_duration_seconds_count[5m]))

# Tiered retention (Mimir/Thanos compactor + store-gateway):
#   HOT   (block storage, 0–15d)  : raw resolution        — incident debugging
#   WARM  (object storage, 15–90d): 5m downsampled        — trends, capacity
#   COLD  (object storage, 90d–1y): 1h downsampled        — YoY, audit
# Raw resolution beyond 15d is almost never queried → downsample, don't delete blindly.
```

### A query/alert that fires on a cardinality or ingest spike (meta-monitoring)

```yaml
# meta-monitoring.yaml — the telemetry bill as a production signal.
groups:
  - name: telemetry-spend
    rules:
      - alert: CardinalityExplosion
        # Series being CREATED fast = a new high-card label just shipped. Leading indicator.
        expr: rate(prometheus_tsdb_head_series_created_total[10m]) > 5000
        for: 5m
        labels: { severity: page }
        annotations: { summary: "Series creation spiking — likely a cardinality bomb in a recent deploy" }

      - alert: IngestRateSpikePerTeam
        expr: |
          sum by (cost_team) (rate(otelcol_receiver_accepted_spans[10m]))
            > 2 * sum by (cost_team) (rate(otelcol_receiver_accepted_spans[10m] offset 1d))
        for: 10m
        labels: { severity: page }
        annotations: { summary: "{{ $labels.cost_team }} ingest 2x'd vs yesterday — check for DEBUG/sampling change" }

      - alert: ErrorTraceKeepRateDropped       # GOODHART GUARD: the fidelity counter-metric
        expr: floor:error_trace_keep_rate < 1.0
        for: 5m
        labels: { severity: page }
        annotations: { summary: "Error-trace keep-rate fell below 100% — a cost change cut a floor signal" }
```

### Cost-model logic comparing per-GB vs per-series pricing (pseudocode)

```python
# cost_model.py — model YOUR usage in EACH vendor's billing unit before signing.
def annual_cost(usage, plan):
    if plan.unit == "series":          # Mimir/Prometheus-style, Grafana Cloud series
        billed = usage.active_series
    elif plan.unit == "gb":            # log-volume / per-GB vendors
        billed = usage.ingest_gb_per_month * 12
    elif plan.unit == "custom_metric": # Datadog: unique name x TAG-VALUE combos
        billed = usage.unique_name_tagset_combos   # the trap: every tag VALUE counts
    elif plan.unit == "event":         # Honeycomb-style: spans/events
        billed = usage.events_per_month * 12

    base = min(billed, plan.commit_units) * plan.committed_rate
    overage = max(0, billed - plan.commit_units) * plan.overage_rate  # 2-5x the cliff
    return base + overage

# Decide on cost-per-fidelity, NOT sticker price:
#   for each vendor: annual_cost(our_real_90d_usage_projected, vendor.plan)
#   + self_host_tco (hardware + a 1.5-FTE platform team)
#   then pick the lowest $ that still keeps the fidelity floor at 100%.
```

---

## Worked Example — A Fleet Telemetry Budget

A 40-service org on a self-hosted Mimir/Tempo/Loki stack, allocating a fixed capacity across teams.

```text
   CAPACITY & RESERVE
   ───────────────────
   Mimir comfortable capacity:   10,000,000 active series
   Reserve (30% headroom):       → governable budget = 7,000,000 series
   Annual fully-loaded cost:     ~$420k (hardware $180k + 1.5-FTE platform team $240k)
   → cost per 1M series ≈ $60k/yr  ← the number that prices every label decision

   ALLOCATION BY TIER  (40 services)
   ─────────────────────────────────
   Tier-1 (8 services, customer-facing): 200,000 series each  = 1,600,000
   Tier-2 (15 services, internal APIs):   80,000 series each  = 1,200,000
   Tier-3 (17 services, workers/cron):    20,000 series each  =   340,000
                                          allocated total     = 3,140,000  (well under 7M — room to grow)

   CHARGEBACK MATH  (showback first, chargeback in year 2)
   ──────────────────────────────────────────────────────
   Team's monthly bill = (team_active_series / 1,000,000) × $5,000   # $60k/yr per 1M, /12
   Checkout (Tier-1, 180k series)  → 0.18 × $5,000 = $900/mo shown on its dashboard
```

### When a team blows its budget — the governance loop

```text
   1. Team hits 80% of its 200k cap        → automated page to the team (not platform)
   2. Team hits 100%                        → SDK View AggregationCardinalityLimit kicks in:
                                              excess attribute sets collapse to otel.metric.overflow
                                              (graceful degradation — NOT a TSDB OOM)
   3. Overflow point appears                → meta-monitor alerts, attributes it to the team
   4. Team either: prunes labels  OR  files an exception PR to the observability guild
   5. Guild ratifies a temporary cap raise (with an expiry) OR the team cleans up
```

The crucial design property: a team blowing *its* budget degrades to *its own* overflow points — it cannot consume the org's 30% reserve or take down the shared TSDB. The fixed capacity is allocated, the per-team cap is enforced in the SDK (before export), and the reserve is the org's shared safety margin, never silently drawn down by one team's mistake.

---

## A Real Cost Incident, Walked Through

**The setup.** A 50-service org, Datadog (per-custom-metric pricing), $48k/month committed spend, overage at 3×. Friday 18:00, the search team ships a "minor" change: a new dashboard needs per-user latency, so an engineer adds `user_id` as a tag on `search.request.duration` — "just to debug a customer complaint." Code review missed it; the org had a wiki rule but no CI cardinality check.

**The footprint.** Within 40 minutes, `search.request.duration` × `user_id` (2.3M active users that evening) mints ~2.3M new custom metrics. Datadog's billing meter starts climbing. Nobody is watching the invoice — it's Friday night.

**The catch (because meta-monitoring existed).** At 18:47 the `CardinalityExplosion` alert fires: `rate(series_created)` for the search namespace is 100× baseline. The on-call SRE is paged — *not* by the invoice, by the telemetry footprint, during the deploy window. The alert annotation names the team and the recent deploy. At 18:55 the SRE correlates the spike to the search team's 18:00 release.

**The rollback.** 19:05: the search team reverts the commit. New series creation stops. The collector's `labeldrop` policy (had it been in the allow-list) would have caught it pre-export, but the search team had a stale overlay — so the revert is the fix. Total exposure: ~70 minutes of overage. Modeled cost of the spike at the 3× overage rate had it run a full month: **~$190k**; actual cost of 70 minutes: a few hundred dollars. Meta-monitoring saved ~$190k.

**The policy that prevents recurrence.**

1. `user_id` (and the rest of the identity allow-list) added to `base/cardinality-allowlist.yaml` as a hard `labeldrop` — the bomb now defuses at the collector *and* the SDK View, before any byte is billed.
2. A **CI cardinality check** added: the search service is scraped in CI, and the build fails on any attribute exceeding 1,000 distinct values in the synthetic soak. The `user_id` tag would have failed the PR.
3. The PR template gains a cardinality-review line item; the observability guild owns the allow-list.
4. The team is shown its `cost.team` dashboard (showback) so the marginal cost of a tag is visible at its desk going forward.

The lesson, stated for the strategy doc: **the wiki rule failed, the structural controls would have caught it three ways, and meta-monitoring was the safety net that turned a $190k mistake into a $300 one.** Defense in depth — allow-list, CI, SDK cap, meta-monitor — is the point.

---

## Coding Patterns

- **Allow-list, never deny-list, at every layer.** Deny-lists are whack-a-mole; the next engineer adds a label you didn't deny. Allow-lists fail closed — anything unlisted is dropped. Org-wide, this is the only safe cardinality posture.
- **Floor-first sampling policy.** Structure every sampling config as `keep-floor` policies first (errors, SLO routes), then cost-saving policies. The floor is inherited by overlays and cannot be overridden — encode that in the base.
- **Time-boxed, scoped overrides.** Team overrides carry an `expires` date that CI enforces, so a launch-week 10% tail rate doesn't become a permanent cost leak nobody remembers.
- **Tag spend at the source.** Inject `cost.team` early in the collector pipeline so every downstream cost number is attributable without a join.
- **Model in the billing unit.** Cost-model code computes the bill in *each vendor's* unit (series / GB / custom-metric / event), never in a generic "data volume."

---

## Clean Code

- **One source of truth for policy.** Sampling, allow-lists, and retention live in *one* GitOps repo with overlays — not scattered across forty service repos. The repo *is* the policy.
- **Policy is tested.** A sampling change ships with a test asserting the floor survives. An untested fidelity change is an unreviewed risk.
- **Every trade-off has an ADR.** What was reduced, to save what, accepting what risk, decided by whom, when. The undocumented trade is the one that becomes a blame search.
- **Self-documenting budgets.** The strategy doc states the capacity, the reserve, the per-tier allocation, and the owner of each lever in plain numbers — not "we try to keep costs reasonable."
- **Meta-monitoring as code.** The cost alerts live beside the app alerts, reviewed the same way.

---

## Best Practices

1. **Make fidelity an explicit, owned, priced decision** — never an inherited default. The fidelity floor is written down and ratified.
2. **Allocate the bill** — showback first, budgets next, chargeback when the org is ready. Stop telemetry being free at the point of use.
3. **Enforce cardinality and sampling as policy-as-code in CI + GitOps**, not in a wiki. The cheap, correct thing is the default and the only thing that merges.
4. **Meta-monitor the bill** as a production signal — alert on series-creation rate, ingest spikes, per-team anomalies, and floor erosion, so you catch the footprint before the invoice.
5. **Pair every cost KPI with a fidelity counter-metric** to neutralize Goodhart. "Cost down *and* coverage flat."
6. **Never sample the SLO signal or the fidelity floor.** Cost discipline stops at the floor's edge; test that every policy change preserves it.
7. **Model build-vs-buy on fully-loaded TCO** (incl. engineer time) and the vendor contract on *your* usage in *their* unit with the overage cliff stress-tested.
8. **Frame trade-offs as priced options for stakeholders** and document the chosen one in an ADR. You compute the options; SRE/product/finance own the choice.

---

## Edge Cases & Pitfalls

- **Chargeback drives under-instrumentation.** If teams are billed but the floor isn't protected, they cut the signals they should keep to save *their* budget. Protect the floor *outside* the chargeable budget.
- **The overage cliff hides in a "good" contract.** A committed discount with a 3× overage rate means one spike costs more than the savings. Model the cliff, not just the commit.
- **Ingest-priced optimization on a series-priced backend** (or vice versa) is wasted effort. Always optimize the unit that bills you.
- **A team override with no expiry** becomes a permanent leak. CI must enforce `expires`.
- **Meta-monitoring on the same backend it monitors.** If the cost spike degrades the backend, your cost alert may not fire. Meta-monitor on an independent, cheap signal path.
- **Showback attribution drifting** as services get renamed/merged — stale `cost.team` tags make the dashboards lie and erode trust in the whole program.
- **Cutting cost on the wrong stage** (retention when ingest is 90% of the bill). Decompose ingest/indexed/retained before optimizing.

---

## Common Mistakes

1. **A bare "reduce cost" KPI** with no fidelity counter-metric — the canonical Goodhart trap; engineers delete needed signal. Cross-ref Engineering Metrics & DORA.
2. **Governing via wiki** instead of policy-as-code + CI. At org scale "please be careful" governs nothing.
3. **Modeling self-hosting as hardware-only** (ignoring the platform team) or SaaS as list-price-only (ignoring overage discipline). Both mislead the build-vs-buy decision.
4. **Signing a contract on the demo dataset's pricing** instead of your own 90-day usage in the vendor's unit with a spike stress-test.
5. **Letting engineers unilaterally decide retention/fidelity** instead of framing it as a stakeholder-owned trade with an ADR.
6. **No meta-monitoring** — the first detector of a cost regression is the invoice, four weeks too late.
7. **Sampling the SLO signal to save money** — corrupts the error budget and every decision built on it.
8. **A shared bill with no allocation** — the tragedy of the commons; no team feels its marginal cost, so the bill grows unchecked.

---

## Tricky Points

1. **Showback changes behavior almost as much as chargeback, at a fraction of the political cost.** Most teams genuinely don't know they're the top producer; visibility alone often fixes it. Climb the ladder in order.
2. **The fidelity floor must live *outside* the chargeable budget**, or chargeback incentivizes cutting it. Floor signals are an org cost, not a team cost.
3. **A cost KPI is safe only when its counter-metric is *downstream*** — MTTR, not just "coverage," is the real test, because coverage itself can be gamed.
4. **Per-host pricing is a trap precisely because it feels cheap** — it ignores cardinality, so teams explode it freely, and the bill detonates at the next renewal or migration to per-series.
5. **Policy-as-code's biggest win is auditability, not enforcement.** Enforcement you could do other ways; "why did fidelity change, by whom, when" is only answerable when policy is versioned.
6. **The marginal cost of fidelity is far lower self-hosted** — which is *why* high-volume orgs keep more data; the build-vs-buy decision changes what fidelity you can afford, not just who runs the stack.

---

## Anti-Patterns at Professional Level

- **The blunt mandate.** "Cut observability 40%" with no counter-metric, no allocation, no floor protection — guarantees the org deletes signal it needs and discovers it during the next incident.
- **The unowned commons.** One central platform line item, no showback, no allocation — every team over-grazes, the bill grows until finance escalates, and the response is the blunt mandate above.
- **Wiki governance.** A beautifully written cardinality policy that lives in Confluence and is enforced by hope. Ships the bomb on the first Friday deploy.
- **The hero's spreadsheet.** One engineer manually audits the bill each month and files cleanup tickets. Doesn't scale, dies when they leave, has no enforcement teeth.
- **Vendor lock-in by accretion.** Adopting proprietary agents/queries/dashboards everywhere, then discovering at renewal the migration cost makes the overage non-negotiable. Keep OTLP/PromQL portability as a strategic hedge.
- **Cost-as-objective.** Treating spend as the goal rather than a constraint, so the observability strategy ("what must we answer") is subordinated to the budget. Inverts the only correct ordering.

---

## Apply it

1. Define the user or business outcome that **Telemetry Cost & Sampling Strategy — Professional (Staff / Principal) Level** should improve.
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

- Which measurable outcome justifies investing in Telemetry Cost & Sampling Strategy — Professional (Staff / Principal) Level?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
