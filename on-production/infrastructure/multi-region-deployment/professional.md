# Multi-Region Deployment — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How do you roll a multi-region topology out across a growing set of service teams as a governed, incremental program rather than a single big-bang cutover, and what measures tell you it's actually working?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

The senior page taught you to choose, per component, which invariant a multi-region design protects during a partition, and to prove that choice with a test. This page is about running that decision as a durable, org-wide program: forty services owned by a dozen teams, each at a different point on the active-active spectrum, a platform team maintaining the routing layer everyone depends on, and a rollout that has to keep delivering value for multiple quarters without anyone having to re-litigate the fundamentals every time a new service joins.

## Making Multi-Region Ownership Stick Organizationally

A multi-region program that isn't owned by name decays into "everyone assumes someone else is watching the replication dashboard." Three things have to be true for ownership to have teeth:

**1. The routing layer has one named platform owner; each service's data-consistency model has one named service owner.** These are different jobs and must not be collapsed into one team. The platform team owns the region-aware router, its health checks, and its own uptime SLA — that's infrastructure shared by everyone. Each service team owns which of the middle-level shapes (single-writer, region-owned, or multi-writer conflict-resolved) applies to *their* data, because only they know their write patterns and what a wrong merge actually costs.

**2. A service can't join active-active rotation without meeting a published readiness checklist.** Without a gate, "we're multi-region now" becomes a claim made by whoever updated the deployment manifest, not a verified state. A minimal checklist that works in practice:

```markdown
# Region-Readiness Checklist — required before a service enters
# active-active rotation in a second region

- [ ] Health check exercises a real dependency (DB, cache), not just process liveness
- [ ] Replication lag is measured and alerting is wired to the platform's
      shared dashboard, not a team-local one nobody else can see
- [ ] For every entity with concurrent-write potential: a merge rule exists
      and has a passing unit test for the tied-timestamp case
- [ ] A partition has been simulated (chaos exercise or staged network
      block) and the observed behavior (refuse vs. locally commit) matches
      the documented, agreed invariant for this service
- [ ] Rollback path exists: the service can be pulled back to single-region
      routing without a data-loss window longer than the agreed RPO
- [ ] On-call runbook updated with the region-specific failure signatures
```

**3. Adding, removing, or reweighting a region for a given service goes through a lightweight, recorded decision — not a quiet routing-weight edit.** The moment cross-region traffic shifting becomes "just change a number in the load balancer config," a team under deadline pressure will shift 100% of traffic to the cheaper region without re-verifying the checklist still holds for the new balance. A short RFC with named sign-off (service owner, platform owner) keeps the history of *why* a weight changed auditable, the same discipline a budget change needs in performance governance.

> **The organizational reality:** multi-region rollouts don't fail because the replication math is wrong. They fail because a service joined active-active rotation without anyone verifying its readiness, a routing weight got changed under pressure with no record, or the platform team and a service team each assumed the other owned a decision that neither actually made.

## Decomposing the Program into Reversible Increments

A single "make everything multi-region" initiative is nearly impossible to schedule, review, or roll back. The workable decomposition mirrors the middle-level shapes, applied service by service, in a fixed order that never skips ahead:

1. **Stand up the routing layer and health checks for a service's stateless tier only**, in the new region, with zero write-path changes. Exit condition: real traffic is being served from both regions, and rolling the routing weight back to 100% single-region takes one config change, verified in a dry run.
2. **Add an asynchronous read replica for the service's primary datastore**, and measure real replication lag under production traffic for at least a full business cycle before trusting it. Exit condition: lag stays within the agreed SLA through at least one real traffic peak, not just a quiet period.
3. **Move specific entities with a demonstrated need to region-owned writes (Shape B)**, one entity type at a time, each with its own before/after latency measurement. Exit condition: the moved entity's cross-region write latency actually dropped, confirmed by measurement, not assumed from the architecture diagram.
4. **Reserve multi-writer conflict resolution (Shape C) for the narrow set of entities that survive the middle-level questions** (real concurrent-write potential, a defined and tested merge rule) — and treat each one as its own reviewed increment, never a bulk migration.
5. **Only after a service completes its checklist does it get added to the platform's active-active service registry**, the single source of truth both the platform team and any auditor consult to know what's actually in active-active rotation right now.

Each step is independently reversible and produces observable evidence before the next one starts — the opposite of a cutover where the first real signal of trouble arrives after every team has already moved.

## Migration, Governance, and Coordination Risks

- **Config drift between regions.** Two regions that started identical drift — a feature flag rolled out in one but not the other, a dependency version mismatch — until "multi-region" quietly becomes "two different systems that happen to share a name." Governance answer: infrastructure-as-code and CI/CD pipelines that deploy to both regions from the same artifact and the same pipeline run, so drift requires an explicit, reviewed exception rather than an accident (the mechanics of that pipeline belong to CI/CD and IaC as topics; this program simply depends on them being disciplined).
- **Data residency overlap.** A region chosen for latency reasons may also happen to satisfy (or violate) a data-residency requirement for users in that jurisdiction — the two concerns are related but not the same, and a rollout plan that only optimizes for latency can accidentally create or break a residency guarantee nobody was tracking. The region-readiness checklist should flag this as a required check-in with whoever owns residency requirements, not something the multi-region program silently decides on its own.
- **Cross-region on-call coordination.** Once a service is genuinely active-active, an incident can originate in either region, and the on-call engineer in one region's time zone may be debugging a problem whose root cause is a partition or a misbehaving peer in a region eight time zones away. A follow-the-sun or explicitly shared on-call rotation, with a runbook that names which region-specific signatures escalate to whom, has to exist before the first real incident, not be improvised during it.
- **Cost governance.** Active-active roughly doubles (or multiplies by region count) the standing compute cost for a service, whether or not that capacity is ever exercised as a failover target. A program that adds regions without a recurring cost review will eventually be asked to justify a bill nobody can explain component by component.

## Outcome Measures and Exit Conditions

A program that can't state its own success in numbers will be judged on vibes, and vibes lose budget arguments. Concrete measures that should be tracked centrally, not per team:

- **Regional traffic share and p50/p99 latency by region** — confirms the routing layer is actually distributing load the way it's configured to, and that users are seeing the latency improvement the program exists to deliver.
- **Replication lag, p50/p99, per replicated entity** — the single number most likely to catch a silently degrading replication link before it causes a read-your-writes complaint.
- **Number of services meeting the full readiness checklist versus number claiming active-active status** — a gap between these two numbers is the clearest signal that governance has a hole in it.
- **Time to roll a service's routing weight back to single-region, measured, not assumed** — this is the exit condition that proves each increment was actually reversible, not just described as reversible in a design doc.
- **Incidents attributable to cross-region causes (split-brain, stale-replica reads, drift) versus incidents avoided by regional failover** — both sides of this ledger matter; a program that only reports the wins is not being honest about its own cost.

## Cross-Team Contracts

- **Platform team → service teams**: the router and health-check infrastructure carry a published SLA (uptime, health-check propagation time); a service team that meets the readiness checklist can rely on that SLA without re-verifying the platform's internals themselves.
- **Service teams → platform team**: each service's registry entry accurately reflects its current shape (A/B/C) and which regions it's actually live in — the platform team routes traffic based on this contract, and a stale or wrong entry is the service team's outage to own, not the platform's.
- **Service teams → residency/compliance owners**: any region addition or traffic reweighting that could plausibly interact with a data-residency requirement is a required check-in, not an assumed pass.
- **On-call → on-call across regions**: a documented handoff and escalation path for incidents whose root cause crosses a region boundary, agreed before an incident, not negotiated during one.

## A Sustained-Delivery Scenario

A marketplace with roughly forty services begins a two-year, staged multi-region program. By quarter three, six services have completed the full readiness checklist and joined active-active rotation; two more have stalled at the replica-lag measurement step because their traffic peaks reveal lag well outside the agreed SLA, and their teams are correctly blocked from proceeding rather than waved through under schedule pressure. A seventh team, eager to hit a launch date, reweights their routing to send 50% of traffic to the new region without completing the partition-simulation checklist item. Three weeks later a real network event partitions that region for eleven minutes; because no one had verified what the service actually does under partition, it turns out to have been quietly committing writes locally on both sides the whole time, and reconciliation after the partition heals requires a manual data-review effort that a completed checklist would have avoided entirely.

The governance response is not to blame the team retroactively — it's to confirm the registry now reflects reality (this service is not, in fact, checklist-complete), require the missed step before the service remains in rotation, and treat the incident as evidence for tightening the gate (should the readiness checklist be enforced by the platform team's rollout tooling, rather than trusted as a self-reported step?) rather than evidence that the checklist itself was unnecessary.

## Decision Frameworks

**Should a service be allowed into active-active rotation? Ask:**
- Has every item on the readiness checklist been independently verified, not self-reported?
- Has a partition actually been simulated and its observed behavior matched against the intended invariant?
- Is replication lag measured against the platform's shared dashboard, not a team-local one?

**Who owns a given decision?**
- Router health, uptime, and cross-service routing SLA → the platform team.
- Which shape (A/B/C) applies to a given entity, and its merge rule → the owning service team.
- Any region change that could touch a residency requirement → a required, recorded check-in with residency/compliance owners.

**How much active-active is enough?**
- Only entities with demonstrated, measured write-latency or availability need justify moving past Shape A. Defaulting everything to multi-writer conflict resolution is the most common and most expensive over-investment in this program.

**When do we add or remove a region?**
- Adding: does it change the quorum math (a genuine partition-tolerance improvement) or only add read capacity (a latency improvement with no consistency benefit)? Both are valid reasons — only one changes the invariant.
- Removing or reweighting: always through the recorded RFC path, never a quiet edit, regardless of how urgent the deadline feels.

## Common Mistakes

1. **Letting a service claim "active-active" without an independently verified readiness checklist.** The gap between claimed and verified status is where split-brain and silent divergence incidents come from.
2. **Collapsing platform ownership and service-data ownership into one team.** Neither the router's uptime nor a service's merge-rule correctness gets the attention it needs when one team is nominally responsible for both.
3. **Treating routing-weight changes as routine config edits.** Without a recorded decision, a deadline-driven reweight can silently violate a residency requirement, an untested partition assumption, or both.
4. **Rolling out multi-region as a single big-bang cutover** instead of the reversible, measured increments outlined here — the first real signal of trouble then arrives after every team has already moved, with no cheap rollback available.
5. **Reporting only the incidents avoided, never the incidents caused by cross-region complexity.** A program that can't show both sides of its own ledger will eventually lose an honest cost argument.
6. **Skipping the residency check-in because the program's stated goal is latency, not compliance.** The two concerns share the same lever (which region serves which traffic) whether or not the program intended to touch both.

## Apply it

1. Define the specific latency or availability outcome the program should improve, in numbers (a target p99 for a named region pair), not a general aspiration.
2. Write a region-readiness checklist for your own context, and name the two owners (platform, service) each checklist item belongs to.
3. Decompose one service's rollout into the reversible increments from this page, and state the exit condition — a specific measurement, not a date — that must be true before each increment proceeds to the next.
4. Draft the cross-team contract that names who is paged first when an incident's root cause could plausibly be cross-region, and how it escalates.
5. Define the recurring measures (traffic share, replication lag, checklist-complete vs. claimed-complete service counts) that will tell you, a quarter from now, whether the program delivered what it promised.

## Verify your work

- The stated outcome in step 1 is a specific number tied to a specific region pair, not a general goal like "improve reliability."
- Every readiness-checklist item in step 2 has exactly one named owner, and no item is owned by both teams or by neither.
- Each increment in step 3 has an exit condition that is a measurement someone would actually check, not an assumed pass.
- A dry run of the cross-team contract from step 4 (a tabletop exercise, not a real incident) surfaces at least one ambiguity worth fixing before it's needed for real.
- The measures from step 5 are actually being collected somewhere a person can look at them today, not planned for "later."

## Review questions

- Why must the platform team's ownership of the routing layer and a service team's ownership of its data-consistency shape remain two separate, named responsibilities?
- What specific evidence would show that a service claiming "active-active" status has actually met its readiness checklist rather than self-reported it?
- Why does a reversible, staged rollout catch a partition-handling gap earlier and more cheaply than a single big-bang cutover would?
- What is the risk of optimizing a region's traffic weighting purely for latency without a required check-in against data-residency requirements?
