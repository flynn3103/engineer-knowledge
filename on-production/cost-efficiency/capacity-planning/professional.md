# Capacity Planning — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How do you run capacity planning as a durable, cross-team practice — with clear ownership, shared forecasting inputs, and evidence that plans stay accurate — instead of a one-off spreadsheet exercise redone in a panic before every big launch?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

> **Roadmap:** [Cost Efficiency](../README.md) → Capacity Planning

*A capacity plan owned by one engineer dies the moment they change teams, and a plan redone from scratch before every launch never gets more accurate. A durable practice is a process with owners, a shared method, and evidence that it's actually improving.*

---

## Core Concept 1 — Ownership Aligned to Cognitive Load

The predictable organizational failure: a central platform or SRE team tries to own every service's capacity forecast, burns out trying to hold operational context they don't have for services they don't run, and every team's plan goes stale the moment that central team's attention shifts elsewhere.

The alignment that holds up:

| Layer | Owner | Responsibility |
|---|---|---|
| **Per-service forecast and headroom target** | The team that operates the service | They have the traffic pattern context and feel the pain first when the plan is wrong |
| **Shared forecasting methodology** | A platform or capacity/SRE team | Define the common template — how growth models get chosen and backtested, what a load-test-derived saturation point must include, what the N-1 invariant statement looks like — so plans are comparable and reviewable across teams |
| **Shared-resource capacity** (a shared database cluster, a shared message broker, a shared egress budget, a shared third-party rate limit) | Whichever team owns that shared resource | Aggregate demand forecasts *from* every consuming team, since no single consumer can see the combined load coming |
| **Program health** | A capacity or SRE working group | Track forecast accuracy and capacity-incident rate across the org; escalate when a team's plan goes stale or a shared resource has no aggregation owner |

This split keeps no team holding more context than it can sustain, and it gives the shared-resource category — the one that individual service teams structurally cannot see on their own — an explicit owner instead of falling through the cracks between teams.

## Core Concept 2 — Decomposing the Rollout Into Reversible Increments

Mandating "every team submits a capacity plan by end of quarter" produces theater: rushed forecasts nobody backtests, written to satisfy a deadline instead of to be useful. Decompose the rollout instead:

1. **Pilot on the single most capacity-constrained service** — the one where a bad forecast caused the most recent near-miss or incident. Motivation already exists, and success is easy to point to.
2. **Extract the forecasting template from the pilot**, not from a committee design session. The pilot reveals which fields actually matter (growth-model choice and backtest result, load-tested saturation point, N-1 invariant statement, shared-resource dependencies) and which were speculative.
3. **Integrate the template into the existing planning cycle** — quarterly business planning, budget review, or roadmap review — rather than inventing a separate capacity-review ritual competing for the same attention.
4. **Expand team by team**, tracking adoption as a ratio (services with a reviewed, backtested plan / total critical services), not as a binary "done."
5. **Only then set an org-wide expectation**, once the template and its integration into planning have survived contact with several real teams and at least one real growth event.

Each step stays independently valuable and reversible: if the template needs a new field after five teams adopt it, that's a template revision, not a program failure, because nothing downstream assumed the first version was final.

## Core Concept 3 — Migration, Governance, and Coordination Risk

Rolling this out across an existing organization surfaces risks a single pilot doesn't:

- **Procurement lead time mismatches.** Cloud capacity can often be added in minutes; reserved-instance commitments, on-prem hardware, or negotiated third-party rate-limit increases can take weeks or months. A capacity plan that doesn't state which category each dependency falls into will discover the mismatch only when it's already too late to order the hardware. This lead-time input is exactly what the sibling Cost Modeling topic needs from capacity planning to reason about committed spend.
- **Compliance and disaster-recovery commitments.** Some regulatory regimes require documented, tested capacity for failover scenarios on critical systems (payments, health data). A capacity plan validated with real load-test and failover-drill evidence is precisely the artifact such an audit expects — but only if it was built to be defensible, with dates and confidence levels, not written retroactively to satisfy a checklist.
- **Coordination cost on shared resources.** The shared-resource layer from Core Concept 1 requires teams that don't normally coordinate to agree on an aggregation owner and a review cadence. Underestimating this is the most common reason a shared database or shared rate limit stays unmodeled even after every individual service's own plan matures.
- **Launch and campaign gating.** A marketing campaign, a major feature launch, or a new market entry can spike demand far outside any steady-state growth curve. Gate these events behind a required capacity-plan update — including a check against any shared resource the new demand will hit — the same way a high-risk deploy might be gated behind an architecture review.

## Core Concept 4 — Outcome Measures and Exit Conditions

A durable practice needs measures that show it's producing real accuracy and real safety, not just paperwork:

```yaml
# Program health dashboard fields, reviewed quarterly.
metrics:
  forecast_accuracy: "abs(projected peak - actual peak) / actual peak, per service, per quarter"
  capacity_incident_rate: "incidents whose root cause was insufficient capacity a plan should have predicted / total incidents"
  overprovision_cost: "avg fleet utilization at peak vs. the plan's headroom target, aggregated cost of the gap"
  shared_resource_coverage: "shared-infrastructure components with a named aggregation owner and a current forecast / total shared components"
  n1_validation_coverage: "critical services with a failover drill confirming the N-1 invariant within the last two quarters / total critical services"
exit_conditions:
  pilot_to_expansion: "pilot service's forecast_accuracy improves over two consecutive quarters, and the template survives one real growth event without a missing field"
  program_maturity: "capacity_incident_rate trending down over two consecutive quarters, and n1_validation_coverage > 80% of critical services"
```

The single most important number is `capacity_incident_rate`: a plan that exists but never prevented a real incident isn't yet earning its cost, no matter how polished its spreadsheet is. `forecast_accuracy` and `overprovision_cost` catch the other half of the failure mode — a plan that's technically never wrong because it wildly over-provisions everything is not a success either. Set the "program is working" exit condition on the incident-rate trend combined with over-provisioning cost, not on either alone.

## Core Concept 5 — Cross-Team Contracts

Once multiple teams' growth affects a shared resource, or one team's launch affects another team's headroom, formalize the handoff the same way an API contract gets formalized:

- Any team expecting a demand spike outside its normal growth curve (a launch, a campaign, a new integration) publishes a **capacity forecast update** to every shared resource it touches, with a **notice window** tied to that resource's own scale-out or procurement lead time — a shared database that takes three weeks to add a replica needs three weeks of notice, not three days.
- The owning team of a shared resource commits to reviewing incoming forecasts and either confirming headroom exists or flagging a conflict before the notice window closes — a forecast submitted and never reviewed is not a contract, it's an email into the void.
- A change to a resource's stated scale-out lead time (a new procurement process, a new region's provisioning taking longer than the old one) goes through the same kind of review as an API breaking change, because for a team planning against the old lead time, it functions as one.
- Accountability follows the contract: if an incident traces back to a shared resource that wasn't warned in time, that's the launching team's action item; if it traces back to a shared-resource owner who received a timely forecast and didn't act on it, that's theirs.

## Core Concept 6 — Sustained Delivery, Not a Static Target

Capacity planning is never "finished" — demand keeps shifting, and the practice has to keep running:

- **Quarterly review per service**, timed against that service's own growth volatility rather than a single fixed org-wide date — a service with a volatile, promotion-driven traffic pattern needs more frequent review than a stable internal tool.
- **Mandatory review trigger on growth events**: a launch, a campaign, a new region, or a new shared dependency opens a capacity-review task automatically, the same way a new invariant might trigger a failure-mode catalog update.
- **Backtesting as the primary accuracy check**, not a one-time model selection. Every quarter's actual peak becomes the next quarter's backtest data point, so `forecast_accuracy` is a trend, not a one-time grade.
- **Program-level retrospective every two quarters** against the outcome measures from Core Concept 4, asking explicitly: is `capacity_incident_rate` actually falling, and if not, which layer — ownership, shared-resource coordination, or the forecasting template itself — is the bottleneck?

---

## Common Mistakes

- **Centralizing every team's forecast in one platform team.** That team burns out holding context it doesn't operationally have, and plans go stale the moment its priorities shift elsewhere.
- **Mandating full coverage before piloting.** Skipping the pilot means the template is designed by committee guesswork, and gets revised painfully after mass adoption instead of cheaply after one team's real experience.
- **Measuring only forecast accuracy, never over-provisioning cost.** A team can hit perfect accuracy by wildly over-buying capacity every time; that's not a success, it's a hidden cost the metric set needs to catch too.
- **Leaving shared-resource capacity unowned.** No single consuming team will claim a shared database or rate limit as "theirs to forecast," so without an explicit aggregation owner this category — often the source of the worst cross-team incidents — goes unmodeled indefinitely.
- **Publishing a capacity forecast contract and never reviewing it.** A notice window nobody actually monitors on the receiving end is not a working contract, it's documentation nobody reads until after the incident.
- **Treating capacity planning as a pre-launch checklist item instead of a sustained practice.** A plan redone from scratch before every big event never gets more accurate, because nothing carries the lessons from one review into the next.

---

## Apply it

1. Choose one real service in your organization whose capacity has caused a near-miss or incident in the past year, and define the two outcome measures you'd track for it: `capacity_incident_rate` and `forecast_accuracy`.
2. Name the owner of that service's own forecast, and separately name the owner of any shared resource (a database, a broker, a rate limit) it depends on that currently has no aggregation owner.
3. Decompose a rollout of this practice to three more teams into reversible increments (pilot, template extraction, planning-cycle integration, expansion), and write the exit condition that moves you from one increment to the next.
4. Draft a one-paragraph capacity forecast contract for that service aimed at one shared-resource owner it depends on: the expected growth, the notice window, and the lead time that notice window is built around.
5. Define the review trigger that would force this plan to be revisited — tie it to a real, recurring event (a launch, a quarterly business review, a backtest miss) rather than a calendar reminder alone.

## Verify your work

- Your outcome measures are specific and falsifiable (a percentage or a rate with a clear numerator and denominator), not a vague "capacity should be fine."
- Every forecast, including shared-resource ones, has a named owner — nothing is orphaned between teams.
- Your rollout plan's exit conditions are concrete enough that someone outside the pilot team could judge whether the pilot actually succeeded.
- Your forecast contract states a notice window derived from an actual lead time, not an arbitrary round number.
- Your review trigger is tied to an event that will actually recur (launches, business reviews, backtest results), not to memory or goodwill.

## Review questions

- Why does centralizing every team's capacity forecast in one platform team tend to fail over time?
- What does tracking over-provisioning cost catch that forecast accuracy alone would miss?
- Why should a shared-infrastructure resource have an explicitly assigned aggregation owner separate from any single consuming team?
- What turns a capacity forecast contract into something a shared-resource owner can actually act on, rather than just a notification?
