# Disaster Recovery — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How do you run a disaster-recovery program across dozens of teams and services so that RTO/RPO targets are actually met and verified on a recurring cadence, without a central team reviewing every drill?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Infrastructure](../README.md) → Disaster Recovery

*A drilled, falsifiable RTO/RPO invariant for one critical path is a senior-level result. Getting forty teams to each own a true invariant for their own services, verified on a real cadence, without a platform team becoming the bottleneck for every drill, is an organizational design problem — and it's the one that actually determines whether the organization survives a real disaster.*

---

## Core Concept 1 — Tier DR requirements to business criticality, not one rule for everyone

A single org-wide rule — "every service needs a 2-hour RTO and a 15-minute RPO, drilled quarterly" — either overburdens low-stakes teams with cost they don't need, or worse, gives high-stakes teams a false sense that the org default is enough when their actual exposure calls for more. The professional move is to tier the requirement to what each service is actually worth if it's unavailable or loses data:

| Tier | Example ownership | Standby tier required | Drill cadence | Required evidence |
|---|---|---|---|---|
| **Tier 1 — revenue/compliance critical** | Checkout, payments, auth | Warm or hot standby | Quarterly, live failover | Timed drill report reviewed by platform team |
| **Tier 2 — customer-facing, non-critical-path** | Search, recommendations, notifications | Warm standby | Biannual, live failover | Timed drill report, self-attested |
| **Tier 3 — internal tooling** | Admin dashboards, internal reporting | Cold standby (backup + restore only) | Annual, or on major change | Post-hoc restore log |

This mirrors how the same organization typically already tiers other blast-radius and rollback policies — the same tiering principle applies to any activity with a real cost of getting it wrong. The point isn't uniform rigor; it's that a Tier 3 team isn't waiting on a platform review to run a routine annual restore test, while a Tier 1 team can't quietly skip its quarterly live failover because nobody's watching.

---

## Core Concept 2 — A standardized DR registration schema as a platform contract

If every team documents its RTO/RPO targets, backup mechanism, and drill history in its own format — a wiki page here, a spreadsheet there, tribal knowledge everywhere else — no one can answer "which services are actually DR-compliant right now" without manually chasing forty teams. The fix is a schema every service registers against, enforced the same way any other platform contract is enforced:

```yaml
# platform-mandated schema — every registered service must declare these fields
service: checkout-api
owner_team: payments
tier: 1
targets:
  rto_minutes: 120
  rpo_minutes: 15
standby:
  type: warm
  promotion_runbook: "runbooks/checkout-api/failover.md"
last_drill:
  date: "2026-05-14"
  measured_rto_minutes: 96
  measured_rpo_minutes: 9
  result: pass
next_drill_due: "2026-08-14"
```

Because the schema is enforced — a registration check flags any Tier 1 service whose `next_drill_due` has passed, or whose last drill result is missing or `fail` — a platform team can build one dashboard covering every service's tier, targets, and drill currency without learning each team's internal tooling. This is what turns the tiering in Concept 1 from an aspiration into something auditable: a Tier 1 service overdue for its quarterly drill is visible immediately, not discovered during the next real disaster.

---

## Core Concept 3 — Rolling out the program as reversible, evidence-gated increments

Mandating this schema, this tiering, and this drill cadence across an existing organization on day one has no early evidence and no way to course-correct if the schema itself needs revision once real teams start using it. Sequence the rollout the same way any cross-org migration should be sequenced:

```text
Increment 1: Ship the registration schema and dashboard. Backfill nothing;
             require it only for newly created services.
             Exit evidence: 100% of new services register within one sprint
             of creation.

Increment 2: Require Tier 1 services (identified from existing incident/
             revenue data, not self-nomination) to register and complete
             one live failover drill.
             Exit evidence: every known Tier 1 service has a registered,
             passing drill result no older than one quarter.

Increment 3: Backfill Tier 2 and Tier 3 registration, self-attested,
             with the platform team spot-checking a sample rather than
             reviewing every one.
             Exit evidence: dashboard coverage reaches an agreed threshold
             of all known services, not just Tier 1.

Increment 4: Wire the schema's "next_drill_due" field into an automated
             reminder and, for Tier 1 only, an escalation if a drill
             goes overdue without an approved exception.
             Exit evidence: overdue Tier 1 drills trigger escalation
             automatically, measured by at least one real overdue case
             being caught before a platform team member noticed manually.
```

Each increment is reversible — you can pause before extending enforcement to the next tier without undoing what's already registered — and each has a measurable exit condition, a dashboard state rather than a date on a project plan. This is the same discipline a technical migration would get, applied to a governance rollout: prove the smallest slice works and produces evidence before asking every team in the organization to comply.

---

## Core Concept 4 — Cross-team contracts: ownership, authority, and accountability

Once DR spans services owned by different teams, several questions need a standing answer *before* an incident, because during one is the worst time to improvise an org chart:

- **Who has the authority to declare a disaster and trigger a cross-service failover?** Typically the on-call engineer for the affected service, using pre-agreed criteria (Core Concept 3 of the senior-level guide) — not an ad hoc escalation chain assembled in the moment.
- **Who owns a shared dependency that many services' failovers rely on** — a shared auth service, a shared DNS/traffic layer, a shared secrets store? That owning team has a standing say over any other team's failover plan that depends on it, exercised through the registration schema (a service can't claim a Tier 1 RTO if its documented dependency chain includes an unregistered or lower-tier shared service) rather than a one-off review meeting.
- **Who is accountable when a drill fails or an invariant is violated during a real event** — the team that owns the service, or the platform team that built the schema and dashboard? A workable split: the owning team is accountable for fixing the immediate gap (a broken runbook, a stale replica); the platform team is accountable for whatever the schema or dashboard failed to catch that let the gap go unnoticed.
- **What's the compliance and audit angle?** Many organizations are subject to external requirements (security certifications, data-retention obligations, customer contractual commitments) that expect documented, periodically tested recovery procedures. The registration schema and drill history double as the artifact that answers an audit request, which is a second, durable reason to keep the dashboard honest beyond internal risk management — without needing to invent specific figures, the general shape ("tested backups, documented RTO/RPO, evidenced on a cadence") is what these reviews consistently expect to see.

Writing these down converts "whose job is this" from a post-incident argument into something anyone can look up.

---

## Core Concept 5 — Outcome measures: proving the program reduces risk, not just that it's adopted

A dashboard showing "90% of services registered" says nothing about whether the organization is actually safer. Track outcomes, not adoption alone:

| Measure | What it tells you | Target shape over time |
|---|---|---|
| **% of Tier 1 services with a passing drill in the last quarter** | Whether the highest-stakes services are actually verified, not just registered | Trending toward 100%, sustained |
| **Measured RTO/RPO vs. target, aggregated across drills** | Whether stated targets reflect reality or are aspirational numbers nobody has hit | Gap shrinking over successive drills |
| **Number of Tier 1 services whose declared dependency chain includes an unregistered shared service** | Whether cross-cutting dependencies are a hidden hole in otherwise-solid individual plans | Trending to zero |
| **Time from a missed drill deadline to escalation firing** | Whether the automated governance is actually working, not just designed | Consistently fast, without needing manual platform-team intervention |
| **Number of Tier 3 teams self-serving their own drills without platform involvement** | Whether tiering is actually reducing central bottleneck load, not just adding process everywhere | Increasing — proves the tiering, not just the schema, is working |

The rollout from Concept 3 is "done," in the same evidence-based sense the senior level applies to a single invariant, when these measures show sustained improvement across multiple quarters — not when the schema has shipped and every team has, in principle, agreed to comply.

---

## Common Mistakes

1. **Applying one RTO/RPO target to every service regardless of what it's worth to the business.** This either overspends on low-stakes services or leaves genuinely critical ones under-protected behind a target that sounds sufficient but isn't.
2. **Letting every team document its DR posture in its own format.** Without a shared, enforced schema, no org-wide dashboard or audit is possible, and nobody can answer "are we actually covered" without chasing every team individually.
3. **Mandating full compliance across every tier on day one.** A big-bang rollout has no early evidence and no way to fix problems in the schema itself before every team is depending on it.
4. **Leaving shared-dependency ownership implicit.** A Tier 1 service's failover plan is only as strong as its weakest, possibly-unregistered shared dependency — and that gap stays invisible until the day it's the reason a "compliant" failover fails.
5. **Measuring registration instead of outcomes.** A dashboard showing high registration coverage says nothing about whether measured RTO/RPO gaps are actually closing, or whether Tier 1 drills are consistently passing.

---

## Apply it

1. Classify the services in one part of your organization into DR tiers based on what it would cost the business if each one lost data or went down for an extended period.
2. Draft a minimal DR registration schema (tier, RTO/RPO targets, standby type, last drill date and result) and a check that flags any Tier 1 service missing a required field or overdue for its drill.
3. Sequence the rollout into at least three reversible increments, each with a measurable exit condition expressed as a dashboard state, not a calendar date.
4. Write down, for one shared dependency multiple teams' services rely on during failover, exactly who owns it and how their standing say over dependent teams' DR plans is enforced mechanically.
5. Define two or three outcome measures (drill pass rate, measured-vs-target RTO/RPO gap, overdue-drill escalation latency) you'll report on quarterly to prove the program is reducing risk, not just that it's been adopted.

## Verify your work

- Every service in scope has an assigned tier with a stated business justification, not a default applied uniformly.
- At least one rollout increment has shipped with a measurable exit condition, and there is evidence that condition was met before starting the next increment.
- The shared-dependency ownership question has a written answer, enforced through the registration schema rather than depending on someone remembering to ask during a review.
- The outcome measures are collected automatically, reviewed on a recurring cadence, and show a real trend — improving, or clearly revealing a gap — rather than a single point-in-time snapshot.

## Review questions

- Why does a single, uniform RTO/RPO target fail an organization whose services have very different criticality?
- What does a shared, enforced DR registration schema make possible that per-team documentation doesn't?
- How would you sequence a DR governance rollout so a flaw discovered in the schema during increment one doesn't force redoing the whole program?
- Which outcome measure would convince you the DR program is actually reducing risk, rather than just being adopted on paper?
