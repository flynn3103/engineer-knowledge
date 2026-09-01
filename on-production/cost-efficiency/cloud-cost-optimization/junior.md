# Cloud Cost Optimization — Junior

<!-- level-focus -->
At junior level, focus on this question:

> Given a single workload and its utilization data, can you choose the right purchasing option and instance size, and tag the resource so its cost can be tracked?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

> **Roadmap:** [Cost Efficiency](../README.md) → Cloud Cost Optimization

*Two identical-looking servers can cost wildly different amounts depending on three decisions: how big it is, how you paid for it, and whether anyone can find it on the bill. This level is about making those three decisions correctly for one resource at a time.*

---

## Core Concept 1 — Vocabulary: The Cloud Billing Levers

Cloud providers do not charge one price for compute. The same instance type can cost several different amounts depending on how you commit to using it. Learn these terms before anything else, because every recommendation in this topic is really just "which of these applies here":

| Lever | What it means | Typical fit |
|---|---|---|
| **On-Demand** | Pay per hour/second, no commitment, cancel anytime | New or unpredictable workloads, short-lived experiments |
| **Reserved Instances (AWS) / Reserved VM Instances (Azure)** | Commit to a *specific* instance family, size, and region for 1 or 3 years for a discount | Steady, well-understood workloads that won't change shape soon |
| **Savings Plans (AWS) / Committed Use Discounts (GCP)** | Commit to a dollar-per-hour *spend* level, flexible across instance family and size, for a discount | Steady workloads whose exact instance shape may still change |
| **Spot Instances (AWS) / Preemptible VMs (GCP) / Spot VMs (Azure)** | Spare provider capacity at a steep discount; the provider can reclaim it with short notice | Interruption-tolerant, stateless, or checkpointed/retryable workloads |
| **Rightsizing** | Matching instance size/family to actually observed CPU/memory/network usage | Every workload, before any purchasing decision |
| **Autoscaling for cost** | Adding and removing capacity to track load instead of running peak-sized capacity constantly | Workloads with variable traffic |
| **Cost allocation tags** | Key-value labels on a resource (team, service, environment) used to attribute spend | Every billed resource |

Two of these are about *how you pay* (on-demand, reserved/savings-plan, spot). One is about *how big the thing is* (rightsizing). One is about *how many you run at once* (autoscaling). One is about *who gets blamed for the bill* (tags). Mixing these up is the single most common junior mistake — you cannot decide "reserved or spot" for a resource until you already know its correct size.

## Core Concept 2 — A Repeatable Method for One Workload

For a single instance or VM, run this loop in order. The order matters — reversing steps 1 and 3 is how teams end up committed to the wrong size for years.

1. **Pull utilization data** for the resource — CPU, memory, and (if relevant) network or disk I/O — over a meaningful window. Two weeks is a reasonable minimum; a single day will miss a weekly batch spike or a weekend traffic dip. Use the provider's own tooling (AWS Compute Optimizer, CloudWatch metrics, GCP recommender, Azure Advisor) rather than guessing from memory.
2. **Rightsize first.** If observed utilization is consistently well below the instance's capacity, pick a smaller size or family before doing anything else. Committing money to the wrong size just locks the waste in for longer.
3. **Classify the workload's tolerance for interruption.** Can it be stopped mid-task and resumed, or restarted from scratch, without losing data or duplicating side effects (a retryable batch job, a stateless web worker behind a load balancer)? If yes, it's a spot candidate. If no, but the load is steady around the clock, it's a commitment candidate (Reserved Instance or Savings Plan / Committed Use Discount). If the load is bursty and unpredictable, stay on-demand and let autoscaling handle the variation.
4. **Tag the resource** with your organization's cost-allocation keys before moving on — team, service, and environment at minimum.
5. **Re-check after applying the change.** Did utilization and the on-demand-equivalent cost move the way you expected? A recommendation you never revisit is just a guess with extra steps.

## Core Concept 3 — Worked Example: an Internal Reporting Service

A small internal reporting job, `myapp-reports`, runs continuously on a single `m5.2xlarge` (8 vCPU, 32 GB memory) instance. Fourteen days of utilization data:

| Metric | Observed (14-day window) |
|---|---|
| CPU average | 11% |
| CPU p95 | 28% |
| Memory average | 40% |
| Memory p95 | 52% |
| Instance | m5.2xlarge (8 vCPU / 32 GB) |

Step 2 (rightsize first) produces a recommendation like the ones a rightsizing tool would surface:

| Current | Recommended | Rationale | Est. footprint change (illustrative) |
|---|---|---|---|
| m5.2xlarge (8 vCPU / 32 GB) | m5.large (2 vCPU / 8 GB) | p95 CPU of 28% and p95 memory of 52% both comfortably fit a 4x-smaller instance with headroom | roughly 75% smaller compute footprint |

Step 3: the workload runs 24/7 with no meaningful traffic variation and can tolerate a short restart (it re-runs its report queue on boot), so after rightsizing it becomes a candidate for a Savings-Plan-style commitment instead of staying on-demand indefinitely.

Step 4, tagging:

| Key | Value |
|---|---|
| `team` | `data-platform` |
| `service` | `myapp-reports` |
| `environment` | `production` |
| `cost-center` | `CC-4821` |

Notice the order: rightsizing happened *before* the commitment decision. Had the team instead bought a 1-year commitment on the original `m5.2xlarge`, they would have locked in the wasted 75% of capacity for a full year.

## Core Concept 4 — When a Recommendation Is Actually Done

A rightsizing-and-purchasing decision for one resource is complete when it has all of these:

1. A **named current instance type and a named recommended instance type** — not "make it smaller."
2. **Utilization evidence** behind the recommendation — an actual CPU/memory number over a real time window, not intuition.
3. A **purchase-option decision with stated reasoning** — which of on-demand, commitment, or spot, and why, referencing the workload's interruption tolerance and load pattern.
4. **Tags applied** using the organization's real schema, not placeholder values.
5. A **way to check the result** — a dashboard, a report, or a follow-up date where you'll confirm the change behaved as expected.

If any piece is missing, the recommendation isn't ready to act on yet.

## Common Mistakes

- **Buying a multi-year commitment before rightsizing.** This locks in whatever size the instance happens to be today — including its waste — for the length of the commitment.
- **Putting a stateful, non-checkpointed workload on spot** and being surprised when an interruption causes data loss or a duplicated side effect. Spot eligibility depends on how the workload behaves when stopped, not on how much money it would save.
- **Rightsizing from too short or unrepresentative a window.** A single weekday misses a weekly batch job's spike; a holiday week misses normal traffic entirely.
- **Skipping tags "for now."** Untagged spend is spend nobody can explain later — by the time someone notices a cost spike, the context for why the resource exists is often gone.
- **Treating rightsizing as a one-time task.** A recommendation made when the service launched can be badly wrong six months later once real traffic patterns are established.

---

## Apply it

1. Pick one instance or VM you control and pull at least 14 days of CPU and memory utilization from your provider's monitoring tool.
2. Produce a rightsizing table like the one in Core Concept 3: current instance type, recommended instance type, and the utilization numbers backing the recommendation.
3. Classify the workload's interruption tolerance and load pattern, and choose one purchasing option (on-demand, commitment, or spot), writing one sentence explaining why.
4. Apply your organization's tagging schema (or the four-key schema above) to the resource with real values, not placeholders.
5. Write a short note stating what you expect to change as a result (footprint, on-demand-equivalent cost) and the specific date or dashboard you'll use to check it in two weeks.

## Verify your work

- The rightsizing table names a specific current and recommended instance type, backed by an actual utilization number, not a guess.
- The purchase-option decision explicitly states the workload's interruption tolerance and load pattern as its reasoning.
- The resource carries every required tag key with a real value.
- You can point to the exact dashboard, report, or follow-up date you will use to confirm the change had the expected effect.

## Review questions

- What is the difference between a purchasing decision (on-demand, commitment, spot) and a sizing decision (rightsizing), and why must sizing come first?
- Why does a workload's interruption tolerance matter more than its cost savings when deciding whether it belongs on spot capacity?
- What four pieces of evidence make a rightsizing-and-purchasing recommendation actually ready to act on?
- Why can a single day of utilization data produce a misleading rightsizing recommendation?
