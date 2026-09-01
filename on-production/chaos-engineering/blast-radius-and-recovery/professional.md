# Blast Radius and Recovery — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How do you operate a blast-radius policy across many teams — governing experiment scope, abort authority, and recovery time — without a central team becoming the bottleneck for every experiment?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Chaos Engineering](../README.md) → Blast Radius and Recovery

*A cell-based architecture and a well-tested circuit breaker are worthless as an org-wide guarantee if each team invents its own abort logic, its own rollback tooling, and its own definition of "small blast radius." At scale, containment is a governance problem before it's a technical one.*

---

## Core Concept 1 — Blast-radius policy tiered to ownership, not applied uniformly

A single organization-wide rule ("every experiment must be scoped to under 5% of traffic") sounds consistent but breaks down immediately: 5% of a payments service's traffic is a materially different risk than 5% of an internal admin tool's traffic. The professional move is to tier the policy to the **blast-radius impact class** the team owns, not to apply one number everywhere:

| Tier | Example ownership | Max experiment scope (unattended) | Abort authority | Required recovery evidence |
|---|---|---|---|---|
| **Tier 1 — revenue/compliance critical** | Payments, checkout, auth | 1 cell or 2% of traffic | On-call, pre-authorized, automatic abort mandatory | Game-day report + automated abort log, reviewed quarterly |
| **Tier 2 — customer-facing, non-critical-path** | Recommendations, search ranking | 10% of traffic | On-call, pre-authorized | Automated abort log |
| **Tier 3 — internal tooling** | Admin dashboards, internal APIs | Up to 100% in staging, 25% in prod | Owning team, no escalation needed | Post-hoc summary |

This mirrors how the same organization typically already tiers rollback policy for releases — the same tiering principle applies to *any* activity with a blast radius, chaos experiments included. The point of tiering is that a Tier 3 team isn't waiting on a central review board to run a harmless staging experiment, while a Tier 1 team isn't allowed to self-certify an experiment that could touch checkout.

---

## Core Concept 2 — A standardized abort-condition schema as a platform contract

If every team defines its own abort logic in its own format, two failures follow: nobody outside that team can review whether the abort condition is actually sound, and no org-wide dashboard can show "which experiments are currently running and what will stop them." The fix is a shared schema, provided as a platform capability rather than reinvented per team:

```yaml
# platform-mandated schema — every registered experiment must declare these fields
experiment:
  owner_team: recommendations
  blast_radius:
    scope: "traffic_percent"
    value: 5
    tier: 2
  abort_condition:
    metric: "error_rate"
    threshold: 0.02
    window: "60s"
    consecutive_breaches: 2
  hard_duration: "10m"
  rollback_action: "kubectl delete networkchaos ${experiment_id}"
  notify_channels: ["#recs-team", "#on-call-status"]
```

Because the schema is enforced (a CI check rejects an experiment definition missing any field), a central platform team can build one dashboard showing every running experiment's tier, scope, and abort condition across the whole org — without needing to understand each team's internal tooling. This is what makes the tiering in Concept 1 auditable rather than aspirational: a Tier 1 experiment missing an automated `abort_condition` fails to register at all.

---

## Core Concept 3 — Decomposing the rollout into reversible, evidence-gated increments

Rolling out blast-radius governance (cell isolation, mandatory abort schemas, tiered policy) across an existing organization of many teams and many services is itself an initiative that needs the same discipline as any other architectural migration — not a single cutover, but a sequence of increments, each producing evidence before the next begins:

```text
Increment 1: Ship the abort-condition schema and the registration CI check,
             enforced for NEW experiments only. Existing ad hoc scripts untouched.
             Exit evidence: 100% of new experiments pass CI registration.

Increment 2: Tier 1 services get mandatory automated abort + cell-isolation review
             as a launch-readiness gate for any new chaos experiment.
             Exit evidence: zero Tier 1 experiments run without automated abort
             for one full quarter.

Increment 3: Backfill existing Tier 1 experiment scripts onto the shared schema.
             Exit evidence: dashboard shows 100% of Tier 1 experiments registered,
             not just new ones.

Increment 4: Extend the mandatory gate to Tier 2. Tier 3 remains self-service,
             deliberately, because the ownership tier says the cost of central
             review there exceeds the risk it prevents.
```

Each increment is reversible (you can pause before extending to the next tier without undoing the previous one) and each has an explicit, measurable exit condition — not "teams feel good about it" but a dashboard percentage. This is the same reversible-increment discipline applied to a governance rollout instead of a code migration: prove the smallest slice works, gate the next slice on evidence, and never mandate the full policy on day one.

---

## Core Concept 4 — Cross-team contracts: who owns abort authority, and who owns the shared blast-radius invariant

The senior level established a blast-radius invariant for one architecture. At the professional level, that invariant spans services owned by different teams, and the organization needs an explicit contract answering questions that have no natural owner otherwise:

- **Who can trigger an abort on a running experiment that's affecting another team's service?** Answer this before an incident, not during one — typically, any on-call engineer for *any* affected service can abort, and the schema's `notify_channels` field ensures the owning team knows immediately.
- **Who owns the cross-cutting dependency (the shared auth service, the shared database) that could turn a Tier 3 experiment into a Tier 1 incident?** The team owning the shared dependency has a standing veto over any experiment that touches it, exercised through the registration CI check rather than a manual approval meeting.
- **Who is accountable when the invariant is violated — the team that ran the experiment, or the platform team that certified the invariant?** A workable answer: the running team owns correcting the immediate incident; the platform team owns updating the shared schema, dashboard, or gate that failed to catch the violation, so the same gap doesn't recur for the next team.
- **What is the escalation path when a Tier 1 abort condition doesn't trip fast enough?** Defined in advance — e.g., automatic page to the platform on-call if any Tier 1 experiment's abort condition takes longer than 90 seconds to fire, independent of whether the owning team's on-call is already engaged.

Writing these down converts "who's responsible" from a post-incident argument into a lookup.

---

## Core Concept 5 — Outcome measures: proving the governance model is working, not just installed

A governance rollout that's shipped but unmeasured is a governance rollout nobody can defend at the next budget review or the next audit. Track outcomes that answer "is this actually reducing risk," not just "is this adopted":

| Measure | What it tells you | Target shape over time |
|---|---|---|
| **% of registered experiments with automated abort** | Adoption of the core safety mechanism | Trending toward 100% for Tier 1/2 |
| **MTTR trend for blast-radius incidents, by tier** | Whether recovery is actually getting faster, not just theoretically faster | Downward trend, tracked quarterly |
| **Blast-radius invariant violations per quarter** | How often an experiment or real failure exceeded its declared scope | Downward trend; each violation has a named root cause |
| **Time from abort-condition breach to registered abort firing** | Whether automated abort is fast in practice, not just present on paper | Sub-90-second median for Tier 1 |
| **Number of teams self-serving Tier 3 experiments without escalation** | Whether the tiering is actually reducing central bottleneck load | Increasing — proves the tiering, not just the gate, is working |

The exit condition for the whole initiative (Concept 3's increments) is evidence-based, not calendar-based: the migration to full governance is "done" when the invariant-violation trend and MTTR trend both show sustained improvement across at least two quarters — not on the date the rollout plan said it would finish.

---

## Common Mistakes

1. **Applying one blast-radius limit to every team regardless of what they own.** A uniform 5%-of-traffic rule either over-restricts low-risk teams or under-restricts high-risk ones. Tier the policy to ownership and impact.
2. **Letting every team invent its own abort-condition format.** Without a shared, enforced schema, no org-wide dashboard or audit is possible, and a central reviewer can't assess a team's safety mechanism without learning their bespoke tooling.
3. **Mandating the full governance model on day one.** A big-bang rollout across every team and every tier has no early evidence and no rollback point if the schema itself needs revision. Sequence it in reversible increments.
4. **Leaving cross-cutting dependency ownership implicit.** If no team explicitly owns "who can veto an experiment touching the shared auth service," that veto doesn't exist until the day it's needed and isn't there.
5. **Measuring adoption instead of outcomes.** A dashboard showing "90% of experiments registered" says nothing about whether MTTR or invariant violations are actually improving. Track both.

---

## Apply it

1. Classify every service in one part of your organization into blast-radius tiers based on what it's worth to the business if its experiment or a real failure escapes its intended scope.
2. Draft a shared abort-condition schema (even five required fields is enough to start) and a CI check that rejects experiment registrations missing them.
3. Sequence the rollout into at least three reversible increments, each with an explicit, measurable exit condition — not a date, a dashboard percentage or a violation count.
4. Write down, for one cross-cutting dependency, exactly which team has veto authority over experiments touching it and how that veto is enforced mechanically (not "they'll ask in Slack").
5. Define the two or three outcome measures (MTTR trend, violation count, abort-latency) you'll report on quarterly to prove the governance model is reducing risk, not just present.

## Verify your work

- Each service has an assigned tier, and the tier's rules are enforceable by a CI check or gate, not by a document nobody reads before running an experiment.
- At least one increment of the rollout has shipped, has a measured exit condition, and has evidence that it was met before the next increment started.
- The cross-cutting dependency's veto is exercised through a mechanism (a gate, a required review from the owning team) rather than depending on someone remembering to ask.
- The outcome measures are collected automatically and reviewed on a recurring cadence, and at least one measure shows a trend (improving or revealing a gap), not just a single snapshot.

## Review questions

- Why does a single, org-wide blast-radius limit fail teams with very different impact profiles?
- What does a shared abort-condition schema make possible that per-team tooling doesn't?
- How would you sequence a governance rollout so a mistake in increment one doesn't force redoing the whole plan?
- Which outcome measure would convince you the governance model is reducing risk rather than just being adopted?
