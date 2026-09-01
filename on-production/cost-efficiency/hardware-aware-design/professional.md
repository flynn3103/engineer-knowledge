# Hardware-Aware Design — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How do you run hardware-aware design as a durable, org-wide practice — with clear ownership, reversible rollout increments, and evidence-based exit conditions — so the fleet keeps matching hardware to workload as both keep changing, instead of freezing at whatever was decided during one migration push?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

*A brilliant one-time migration, led by one platform engineer, ages the moment that engineer moves teams and the next instance generation ships. A durable practice is an operating model with owners, a rollout playbook, and a reason every team keeps re-checking their own hardware fit.*

---

## Core Concept 1 — Ownership Aligned to Cognitive Load

The organizational failure mode here is familiar: a central platform team tries to own every service's instance-family and architecture decisions, burns out tracking workload details they don't operate, and the fleet drifts back out of alignment the moment that team's attention shifts elsewhere.

| Layer | Owner | Responsibility |
|---|---|---|
| **Per-service profiling and instance choice** | The team that operates the service | They have the operational context on how the workload actually behaves under real traffic; they own re-profiling when the workload's shape changes |
| **Multi-arch build pipeline and instance-family catalog** | A platform/infrastructure team | Publish which instance families and CPU architectures are supported, keep the CI/CD pipeline able to build and test for each, and retire support for a family only with notice |
| **Cross-cutting contention and capacity risk** | Whichever team owns fleet-wide capacity and placement | Noisy-neighbor patterns, NUMA-sensitive large-instance workloads, and instance-family deprecation risk cut across services — no single service team can see or fix these alone |
| **Program health** | A FinOps or platform working group | Track adoption, staleness of profiling data, and validated-savings numbers across the org; escalate when a team's hardware choice hasn't been reviewed in a long time relative to how often that service changes |

The point of this split: no team holds more context than it can sustain, and the cross-cutting risks — the ones that don't belong to any single service — have an explicit owner instead of falling through the gap between teams.

## Core Concept 2 — Decomposing the Initiative Into Reversible Increments

Rolling out hardware-aware design (or a specific push like an ARM/Graviton migration) as one mandate — "every service re-evaluates its instance family by end of quarter" — produces theater: rushed re-sizing decisions nobody validates, made to satisfy a deadline instead of to actually save money or improve performance. Decompose it instead:

1. **Pilot on one well-understood, low-risk service.** Pick a stateless, well-monitored service with no native dependencies, ideally one whose team already suspects it's mismatched to its current hardware — motivation is present and success is easy to demonstrate.
2. **Extract the playbook from the pilot, don't design it in a committee first.** The pilot reveals which profiling signals actually mattered, which dependency checks were necessary, and what the canary comparison window needed to look like — write the reusable checklist from what worked, not from a whiteboard guess.
3. **Fold the playbook into the platform team's build pipeline** before expanding to more teams: multi-arch build support, a standard canary-comparison dashboard template, and a documented rollback mechanism become defaults every subsequent team can pick up without rebuilding them.
4. **Expand service by service, tracking adoption as a ratio** (services with a current, validated hardware-fit review / total services) rather than a binary "migrated or not."
5. **Only then set a standing expectation** — periodic re-review tied to deploy frequency, not a one-time program with an end date — once the playbook has survived contact with several real teams.

Each step stays independently valuable: if the canary-comparison template needs a new metric after the fifth team uses it, that's a template revision, not a program failure, because nothing downstream assumed the first version was final.

## Core Concept 3 — Migration, Governance, and Compliance Risk

Rolling this out across an existing organization surfaces risks a single pilot doesn't:

- **Stranded reserved-capacity commitments.** If your org has committed to reserved instances or savings plans tied to a specific instance family, a hardware-aware migration away from that family can strand the commitment financially — this decision needs to be coordinated with whoever owns the reserved-capacity portfolio, not made unilaterally by a service team chasing a better price-performance ratio.
- **License and support constraints.** Some commercial software (certain databases, monitoring agents, specialized runtimes) is licensed or supported only for specific CPU architectures. A migration plan has to check license terms and vendor support commitments before assuming a workload can move, not after.
- **Security and compliance re-certification.** A new instance family or architecture may fall outside an existing security-scanning pipeline's coverage, or outside a compliance audit's previously certified infrastructure baseline. For regulated workloads, this can mean a formal re-certification step is required before production traffic is allowed on the new hardware — treat this as a gating dependency in the rollout plan, not an afterthought discovered during audit season.
- **Coordination cost across teams sharing fleet capacity.** Instance-family choices interact with autoscaling pools, spot-capacity strategy, and shared-host placement policies that no single service team controls. Underestimating this coordination is the most common reason the "cross-cutting contention" ownership layer from Core Concept 1 stays theoretical instead of actually staffed.
- **Change freezes and release gating.** If deploys to regulated or high-risk systems are gated behind an architecture review, a hardware-family change should trigger that same review — otherwise the fleet's actual hardware composition silently drifts ahead of what governance believes is running.

## Core Concept 4 — Outcome Measures and Exit Conditions

A durable program needs measures that show whether it's producing real efficiency gains, not just migration activity:

```yaml
# Program health dashboard fields, reviewed quarterly.
metrics:
  hardware_fit_coverage: "critical services with a hardware-fit review in the last N months / total critical services"
  validated_savings: "cost delta measured from actual canary/production comparison, not vendor list-price claims"
  regression_rate: "migrations that required rollback or caused a latency/correctness regression / total migrations attempted"
  staleness: "median time since last profiling review per service, relative to that service's deploy frequency"
  cross_cutting_incident_rate: "incidents traced to noisy-neighbor, NUMA, or instance-family deprecation / total incidents"
exit_conditions:
  pilot_to_expansion: "pilot service shows validated savings confirmed by a full peak-cycle canary, with zero unresolved correctness regressions"
  program_maturity: "regression_rate trending down over two consecutive quarters, and hardware_fit_coverage above an agreed threshold for critical services"
```

The measure worth anchoring the program to is `validated_savings` from real canary comparisons, not projected savings from a vendor's price sheet — a migration that looks good on a spreadsheet and regresses in production has produced negative value even if the instance itself is cheaper per hour. Pair it with `regression_rate`: a program pushing migrations fast while regression rate climbs is trading measured savings for unmeasured incident cost, and the exit condition for "the program is mature" should require both moving in the right direction together, not either one alone.

## Core Concept 5 — Cross-Team Contracts

Once multiple teams depend on the platform team's instance-family catalog and multi-arch build pipeline, formalize the relationship the same way an API contract would be:

- The platform team publishes a **supported hardware catalog**: which instance families and architectures are build-pipeline-supported today, which are in deprecation with a stated timeline, and which are experimental (available but not yet validated at scale).
- Service teams commit to **profiling before requesting a new instance family or architecture** — a request without a profiling table (from the middle-level composite-profiling method) doesn't get platform-team support, the same way an API change without a spec doesn't get reviewed.
- A **deprecation of a supported hardware family** goes through the same notice period and migration-assistance process as a breaking API change, because for a team whose autoscaling pool depends on that family, it functionally is one.
- **Accountability follows the contract**: if an incident traces back to the platform team retiring a family without adequate notice, that's the platform team's action item; if it traces back to a service team migrating without profiling or without checking the dependency-audit step, that's the service team's.

## Core Concept 6 — Sustained Delivery, Not a Static Target

Hardware-aware design is never "done" — new instance generations ship roughly every couple of years, workload shapes change as features are added, and the org's fleet composition needs to keep tracking both. A sustainable cadence:

- **Re-review tied to each service's own deploy frequency**, not a fixed org-wide calendar date — a service deploying weekly and adding features regularly needs more frequent hardware-fit attention than one that's stable and deploys quarterly.
- **Mandatory review trigger on workload-shape change**: a new feature that measurably shifts a service's resource profile (adding a memory-heavy caching layer to a previously CPU-bound service, for instance) should open a hardware-fit review automatically, the same way a schema change might trigger a migration review.
- **Deprecation-driven reviews as a primary maintenance mechanism**: when the platform team announces an instance-family deprecation, every team using that family gets a scoped, time-boxed review — this keeps the fleet's hardware composition current without a separate "hardware audit day" competing for attention against feature work.
- **Program-level retrospective every couple of quarters** against the outcome measures from Core Concept 4, asking directly: is validated savings actually growing while regression rate holds steady or falls, and if not, which layer — ownership, the playbook, or cross-team coordination — is the bottleneck?

---

## Common Mistakes

- **Centralizing every service's hardware decision in one platform team**, which then can't sustain operational context across dozens of services and lets the fleet drift the moment that team's priorities shift.
- **Mandating full-fleet re-evaluation before piloting**, producing a rollout playbook designed by guesswork that has to be painfully revised after mass adoption instead of cheaply refined after one team's real experience.
- **Measuring migration activity (number of services moved) instead of validated savings and regression rate**, which rewards migrating quickly over migrating safely.
- **Leaving reserved-capacity, licensing, and compliance re-certification out of the rollout plan**, discovering a stranded financial commitment or a failed audit only after the migration is already in production.
- **Treating the program as a one-time initiative with an end date**, rather than a standing practice tied to deploy frequency and hardware-generation turnover — the fleet drifts back out of alignment within a couple of years either way.
- **Leaving cross-cutting contention risk (noisy-neighbor, NUMA, deprecation) unowned**, because no single service team will claim it as theirs, and it becomes the source of the incidents nobody saw coming.

## Apply it

1. Choose one real hardware-related initiative in your org (an ARM migration, a right-sizing push, a response to an instance-family deprecation notice), and define the validated-savings and regression-rate measures you'd use to judge whether it actually helped, not just whether it shipped.
2. Assign a named owner for the pilot service's hardware decision, and separately name the owner for the cross-cutting contention risk category that no single service team currently claims.
3. Decompose the rollout into at least three reversible increments (pilot, playbook extraction, pipeline integration, expansion) with a stated exit condition moving from one to the next, rather than a single deadline-driven mandate.
4. Identify at least one governance risk specific to your org (a reserved-capacity commitment, a license constraint, a compliance re-certification requirement) that the rollout plan must account for before expanding past the pilot.
5. Draft the supported-hardware-catalog contract your platform team would publish: which families are supported, which are deprecating with what notice period, and what a service team must provide (a profiling table) before requesting a new one.

## Verify your work

- The outcome measures you defined are specific and falsifiable (a rate or a delta with a clear numerator and denominator), not a vague "improved efficiency."
- Every layer of ownership from Core Concept 1 has a named owner in your answer, including the cross-cutting contention layer — nothing is implicitly "everyone's problem."
- The rollout plan's exit conditions are concrete enough that someone outside the pilot team could judge, from the data alone, whether the pilot succeeded.
- The governance risk you identified names the specific mechanism (a contract clause, a compliance control, a licensing term) that would actually block or complicate the migration, not a generic "there might be compliance issues."
- The hardware catalog draft is specific enough that a service team could self-serve a decision about whether to request a new family, without a synchronous conversation with the platform team first.

## Review questions

- Why does centralizing every service's hardware decisions in one platform team tend to fail as the organization scales?
- Why should validated savings from a real canary be trusted over a vendor's list-price price-performance claim when judging whether a migration succeeded?
- What governance risks specific to hardware migrations (beyond compliance in general) does a rollout plan need to account for before expanding past a pilot?
- Why does treating hardware-aware design as a one-time initiative rather than a standing practice lead the fleet back out of alignment over time?
