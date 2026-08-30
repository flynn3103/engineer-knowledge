# Autoscaling — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How do you run autoscaling as a governed, cross-team practice — with clear policy ownership, safe default guardrails, and evidence that scaling decisions are reducing cost and incidents — instead of every team hand-tuning its own thresholds in isolation until something breaks?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core Concept 1 — Ownership Aligned to Cognitive Load

The predictable organizational failure: a platform or SRE team tries to own every service's HPA thresholds directly, ends up hand-tuning configuration for workloads whose traffic pattern they don't operationally understand, and every threshold quietly drifts out of date the moment that team's attention moves elsewhere.

The split that holds up:

| Layer | Owner | Responsibility |
|---|---|---|
| **Per-service scaling signal and thresholds** | The team that operates the service | They understand the workload's real bottleneck (CPU, queue depth, connection count) and feel the pain first when a threshold is wrong |
| **Shared autoscaling defaults and templates** | A platform team | Own the baseline HPA/KEDA `ScaledObject` template, the standard `behavior` policy shape (asymmetric scale-up/scale-down), and the Cluster Autoscaler / node-pool configuration every service scales into |
| **Shared downstream resource ceilings** (a shared database's connection limit, a shared message broker's throughput, a shared third-party rate limit) | Whichever team owns that shared resource | Publish the resource's real capacity limit so consuming teams can derive a correct `maxReplicas`, and track aggregate demand across every consumer, since no single service team can see the combined load |
| **Program health** | A platform or SRE working group | Track thrashing incidents, scale-storm drill coverage, and cost-per-scaled-instance-hour across the org; escalate when a service's `maxReplicas` was never derived from a real ceiling |

This keeps no single team holding more operational context than it can sustain, and it gives the shared-resource-ceiling category — the one no individual service team can see on its own — an explicit owner instead of leaving it to be discovered during an incident.

## Core Concept 2 — Decomposing the Rollout Into Reversible Increments

Mandating "every service adopts the standardized autoscaling template by end of quarter" produces theater: configuration copied in to satisfy a deadline, never tuned against the service's real bottleneck. Decompose it instead:

1. **Pilot on the service with the clearest recent pain** — one that either thrashed visibly, hit `maxReplicas` during a real surge, or is still scaled manually because nobody trusted an autoscaler with it. Motivation already exists.
2. **Extract the template from the pilot**, not from a committee design session — the pilot reveals which `behavior` policy shape, which metric types, and which review fields (a documented `maxReplicas` derivation, a scale-storm drill result) actually matter in practice.
3. **Integrate the template into the existing deployment pipeline** (a Helm chart default, a GitOps-managed base manifest) rather than inventing a separate autoscaling-review ritual competing for attention with normal delivery.
4. **Expand service by service**, tracking adoption as a ratio (services on the standardized template with a derived `maxReplicas` / total services with variable load), not as a binary "done."
5. **Only then set an org-wide default**, once the template has survived contact with several real teams and at least one real scale-storm drill.

Each step stays independently valuable and reversible: if the template needs a new field after five teams adopt it, that's a template revision, not a program failure, because nothing downstream assumed the first version was final.

## Core Concept 3 — Migration, Governance, and Coordination Risk

Rolling this out across an existing organization surfaces risks a single pilot doesn't:

- **Manual-to-autoscaled migration risk.** Services still scaled by a human running `kubectl scale` on a schedule or by gut feel often have no documented bottleneck signal at all. Migrating them needs an explicit step — measure the real bottleneck first (Middle Concept 1's signal-choice table) — rather than defaulting straight to a CPU-based HPA because it's the path of least resistance.
- **Cost guardrails.** An uncapped or poorly-ceilinged autoscaler is a mechanism for turning a traffic spike, a retry storm, or a misconfigured client into an uncontrolled cloud bill. A governance guardrail — a required `maxReplicas` derivation reviewed against both cost and the downstream resource ceiling from Senior Concept 1 — belongs in the same review process as a production deploy, not left to individual discretion.
- **Compliance and audit commitments.** Regulated workloads (payments, health data) sometimes require documented, tested capacity behavior under load, including how autoscaling behaves during a dependency failure and recovery. A scale-storm drill record with a date and a result is exactly the artifact such an audit expects — but only if teams were already running these drills for their own reasons, not producing one retroactively to satisfy a checklist.
- **Coordination cost on shared resources.** The shared-resource-ceiling layer from Core Concept 1 requires teams that don't normally coordinate to agree on who publishes the limit and how often it's re-validated. Underestimating this is the most common reason a shared database's connection ceiling stays undocumented even after individual services' own autoscaling matures.

## Core Concept 4 — Outcome Measures and Exit Conditions

A durable practice needs measures that show it's producing real safety and real savings, not just more YAML:

```yaml
# Autoscaling program health dashboard, reviewed quarterly.
metrics:
  thrashing_incident_rate: "scale up/down cycles under 5 min apart, per service, per week"
  maxreplicas_derivation_coverage: "services whose maxReplicas traces to a documented shared-resource ceiling / total autoscaled services"
  scale_storm_drill_coverage: "critical services with a passed scale-storm drill in the last two quarters / total critical services"
  cost_per_scaled_instance_hour: "compute cost attributable to autoscaled workloads vs. a fixed-capacity baseline for the same traffic"
  scale_event_slo_violation_rate: "SLO breaches that occurred during an active scaling event / total scaling events"
exit_conditions:
  pilot_to_expansion: "pilot service's thrashing_incident_rate reaches zero over two consecutive quarters, and the template survives one real traffic surge without a missing field"
  program_maturity: "maxreplicas_derivation_coverage and scale_storm_drill_coverage both exceed 80% of critical services"
```

The single most important pairing is `maxreplicas_derivation_coverage` against `cost_per_scaled_instance_hour`: a program can hit perfect derivation coverage by setting every ceiling conservatively low, which shows up as high cost-per-hour from constant near-max operation — that's not success, it's a different failure the metric set has to catch. Set the "program is working" condition on the combination, not on derivation coverage alone.

## Core Concept 5 — Cross-Team Contracts

Once one team's scaling ceiling depends on another team's shared resource, formalize the handoff the same way an API contract gets formalized:

- Any service team deriving a `maxReplicas` from a shared resource's ceiling (a database's `max_connections`, a broker's throughput limit, a partner API's rate limit) publishes that derivation to the resource's owning team — not just to their own repo — so the owning team can validate the combined demand across every consumer.
- The shared-resource owner commits to reviewing incoming derivations and confirming the aggregate still fits within the resource's real capacity, or flagging a conflict, within a stated turnaround time. A derivation submitted and never reviewed is not a contract — it's a spreadsheet nobody checked.
- A change to a shared resource's actual limit (a database migration that changes `max_connections`, a renegotiated rate limit) triggers a review of every consuming service's `maxReplicas`, the same way an API breaking change triggers a review of every caller.
- Accountability follows the contract: if an incident traces back to a `maxReplicas` never derived from a real ceiling, that's the service team's action item; if it traces back to a shared-resource owner who received a valid derivation and never flagged that the aggregate no longer fit, that's theirs.

## Core Concept 6 — Sustained Delivery, Not a Static Target

Autoscaling configuration is never "finished" — traffic patterns shift, dependencies change capacity, and the practice has to keep running:

- **Review trigger on real events**, not a calendar alone: a new downstream dependency added to a service, a thrashing incident, a scale-storm drill that didn't hold, or a shared resource's capacity changing all reopen that service's autoscaling review automatically.
- **Scale-storm drills as a recurring practice**, not a one-time certification — the same drill run again after a service's dependency graph changes is what catches a `maxReplicas` that quietly became unsafe.
- **Template revisions carried forward, not re-litigated per team.** When a pilot or an incident reveals the standard template is missing a field (an asymmetric scale-down policy, a documented ceiling derivation), that revision propagates to every service on the template, rather than each team discovering the gap independently.
- **Program-level retrospective every two quarters** against the outcome measures from Core Concept 4, asking explicitly: is `thrashing_incident_rate` actually falling, and if not, which layer — signal choice, policy tuning, or an undocumented shared-resource ceiling — is the bottleneck?

---

## Common Mistakes

- **Centralizing every service's threshold tuning in one platform team.** That team lacks the operational context to tune workloads it doesn't run, and thresholds drift stale the moment its priorities shift elsewhere.
- **Mandating full template adoption before piloting.** Skipping the pilot means the template is designed by guesswork and gets painfully revised after mass adoption instead of cheaply after one team's real experience.
- **Measuring only derivation coverage, never cost.** A program can hit perfect `maxReplicas` derivation coverage by setting every ceiling conservatively low — that's a cost problem hiding behind a compliance-looking metric.
- **Leaving shared-resource ceilings unowned.** No individual service team will claim a shared database's connection limit as "theirs to publish," so without an explicit owner this is the category most likely to cause a cross-team incident.
- **Treating a scale-storm drill as a one-time certification.** A drill that passed once, before a service's dependency graph changed, gives false confidence about the system today.
- **Publishing a maxReplicas derivation and never having it reviewed.** A ceiling nobody on the shared-resource side actually checked is documentation, not a working contract.

---

## Apply it

1. Choose one real service in your organization that autoscales but whose `maxReplicas` was never explicitly derived from a downstream shared resource's limit, and calculate what that derivation would actually be.
2. Name the owner of that service's own scaling configuration, and separately name the owner of the shared resource it depends on — flag if that owner doesn't currently exist.
3. Decompose a rollout of a standardized autoscaling template to three more teams into reversible increments (pilot, template extraction, pipeline integration, expansion), and write the exit condition that moves you from one increment to the next.
4. Define the two outcome measures you'd track for this rollout — `thrashing_incident_rate` and `maxreplicas_derivation_coverage` — with a concrete numerator and denominator for your organization.
5. Draft a one-paragraph cross-team contract between this service and its shared-resource owner: what gets published, how often it's re-validated, and what happens if a change on either side breaks the agreement.

## Verify your work

- Your `maxReplicas` derivation shows explicit arithmetic tied to a real shared-resource limit, not a round number.
- Every scaling configuration you reviewed, including shared-resource ceilings, has a named owner — nothing is orphaned between teams.
- Your rollout plan's exit conditions are concrete enough that someone outside the pilot team could judge whether the pilot actually succeeded.
- Your outcome measures have clear numerators and denominators, not a vague "autoscaling should be safer."
- Your cross-team contract states a re-validation trigger tied to a real event (a dependency change, an incident), not to memory or goodwill.

## Review questions

- Why does centralizing every service's autoscaling threshold tuning in one platform team tend to fail over time?
- What does tracking cost-per-scaled-instance-hour catch that maxReplicas-derivation coverage alone would miss?
- Why should a shared downstream resource have an explicitly assigned owner separate from any single consuming service team?
- Why does a scale-storm drill need to be a recurring practice rather than a one-time certification?
