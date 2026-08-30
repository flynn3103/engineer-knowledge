# Failure Modes — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How do you run a failure-mode catalog as a durable, org-wide practice with clear ownership, so it stays current and drives real resilience investment instead of becoming a stale document?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

> **Roadmap:** [Chaos Engineering](../README.md) → Failure Modes

*A brilliant catalog owned by one architect dies the day they change teams. A durable catalog is a practice with owners, a schema, and a reason every team keeps updating it.*

---

## Core Concept 1 — Ownership Aligned to Cognitive Load

The organizational failure mode of failure-mode catalogs is predictable: a central architecture or SRE team tries to own everyone's catalog, burns out maintaining knowledge of services they don't operate, and the catalog goes stale the moment that team's attention moves elsewhere.

The alignment that actually holds:

| Layer | Owner | Responsibility |
|---|---|---|
| **Per-service entries** | The team that operates the service | Keep their own service's failure modes current; they have the operational context and feel the pain first |
| **Shared taxonomy and schema** | A platform or SRE team | Define the common format (the fields every entry must have, the severity/likelihood scale, the invariant-linking convention) so catalogs are comparable across teams |
| **Cross-cutting correlated failure modes** | Whichever team owns the shared resource (a shared cache, a shared connection pool, a shared queue) | Document what shares the resource and what happens under contention — this is the category no single service team can see alone |
| **Program health** | SRE or a resilience working group | Track adoption, staleness, and validation coverage across the whole org; escalate when a team's catalog goes stale or a shared-resource entry has no owner |

The point of this split: no team is asked to hold more context than their own cognitive load can sustain, and no failure mode falls through the cracks between teams because the shared-resource layer explicitly has an owner too.

## Core Concept 2 — Decomposing the Program Into Reversible Increments

Rolling out an org-wide catalog practice as one mandate ("every team documents failure modes by end of quarter") produces theater: rushed, low-quality entries nobody validates, written to satisfy a deadline rather than to be useful. Decompose it instead:

1. **Pilot on one critical service.** Pick the team and service where a catalog would have prevented the most recent bad incident — motivation is already present, and success is easy to point to.
2. **Extract the schema from the pilot**, don't design it up front in a committee. The pilot reveals which fields actually get used (invariant links, confidence level, shared-resource flags) and which were speculative.
3. **Integrate the schema into the postmortem process** before expanding to more teams: every postmortem's action items must include "update the catalog" as a checklist item, with the specific entry added or corrected. This is what keeps catalogs current without a separate maintenance ritual competing for attention.
4. **Expand team by team, reusing the schema**, tracking adoption as a number (services with a reviewed catalog / total services), not as a binary "done."
5. **Only then set an org-wide expectation**, once the schema and the postmortem hook have both survived contact with several real teams and real incidents.

Each step is independently valuable and reversible — if the schema needs to change after five teams adopt it, that's a schema revision, not a program failure, because nothing downstream was built assuming the first version was final.

## Core Concept 3 — Migration, Governance, and Compliance Risk

Rolling this out across an existing organization surfaces risk categories that a single-team pilot doesn't:

- **Legacy services with undocumented dependencies.** Older services often have call graphs nobody fully remembers; the catalog effort for these has to start with rediscovering the dependency graph from live traffic (service mesh, APM) before any failure mode can even be named accurately.
- **Compliance and audit requirements.** Some regulatory regimes require documented failure analysis and disaster-recovery reasoning for critical systems (payments, health data). A properly maintained failure-mode catalog, tied to invariants and validated with evidence, is exactly the artifact an audit asks for — but only if it was built to be defensible, with confidence levels and dates, not written retroactively to satisfy a checkbox.
- **Coordination cost across teams sharing infrastructure.** The shared-resource layer from Core Concept 1 requires teams that don't normally talk to agree on an owner and a review cadence. Underestimating this coordination cost is the single most common reason the shared-failure-mode category stays empty even after individual service catalogs mature.
- **Change freezes and release gating.** If your org gates high-risk deploys behind an architecture review, a new dependency or a new shared resource should trigger a required catalog update as part of that review — otherwise the catalog silently falls behind the system it describes.

## Core Concept 4 — Outcome Measures and Exit Conditions

A durable program needs measures that show whether it is producing real resilience, not just paperwork:

```yaml
# Program health dashboard fields, reviewed quarterly.
metrics:
  catalog_coverage: "critical services with a reviewed catalog / total critical services"
  validation_coverage: "catalog entries confirmed by incident or fault-injection experiment / total entries"
  staleness: "median days since last catalog review, per service, vs. that service's deploy frequency"
  surprise_incident_rate: "incidents whose root cause was NOT in the catalog beforehand / total incidents"
  shared_resource_ownership: "shared-infrastructure components with a named catalog owner / total shared components"
exit_conditions:
  pilot_to_expansion: "pilot team's catalog has >= 3 entries confirmed by an actual experiment, and one postmortem successfully used it"
  program_maturity: "surprise_incident_rate trending down over two consecutive quarters, and catalog_coverage > 80% of critical services"
```

The single most important number is `surprise_incident_rate`: a catalog that exists but never predicted a real incident is not yet doing its job, no matter how many rows it has. Coverage and validation are leading indicators; the surprise-incident trend is the outcome measure that proves the leading indicators mean something. Set the exit condition for "the program is working" on that trend, not on coverage percentage alone — a team can reach 100% coverage with shallow, unvalidated entries and still be surprised by every incident.

## Core Concept 5 — Cross-Team Contracts

Once multiple teams depend on each other's services, a failure-mode catalog entry for "what happens when Team A's service misbehaves" is only as good as Team A's willingness to keep it accurate. Formalize this the same way API contracts are formalized:

- Every service that other teams depend on publishes a **failure-mode contract** alongside its API contract: declared timeout behavior, what a caller should expect under slow-vs-down-vs-erroring conditions, and which of its own failure modes are considered "stable" (won't change without notice) versus "may change as we evolve internals."
- Consuming teams are expected to design their own resilience (timeouts, circuit breakers, fallbacks) against the *declared* contract, not against whatever the dependency happens to do today — this is what makes the contract enforceable and gives the owning team room to change their internals without breaking every consumer's assumptions.
- A contract change (e.g., a dependency team changing its timeout default, or adding a new failure mode class) goes through the same review as an API breaking change, because for a consumer relying on the old behavior, it effectively is one.
- Accountability follows the contract: if an incident traces back to a dependency behaving outside its declared failure-mode contract, that's the owning team's action item; if it traces back to a consumer that never designed against the published contract, that's the consumer's.

## Core Concept 6 — Sustained Delivery, Not a Static Deliverable

The catalog is never "finished" — the program has to keep running as the system keeps changing. A sustainable cadence:

- **Quarterly review per service**, timed against that service's own deploy frequency rather than a fixed calendar date for the whole org — a service that deploys weekly needs more frequent catalog attention than one that deploys quarterly.
- **Mandatory review trigger on architecture change**: a new dependency, a new shared resource, or a new invariant (a new payment method, a new data-residency requirement) opens a catalog-review task automatically, the same way adding a new API endpoint might trigger a contract-test requirement.
- **Postmortem-driven updates** as the primary maintenance mechanism, not a separate "catalog day." This keeps the catalog's growth tied to real evidence instead of speculative brainstorming sessions that produce entries nobody later validates.
- **Program-level retrospective** every two quarters against the outcome measures from Core Concept 4, with the explicit question: is the surprise-incident rate actually falling, and if not, which layer (schema, ownership, coordination on shared resources) is the bottleneck?

---

## Real-World Examples

- **Pilot success drives adoption.** A payments team's pilot catalog, integrated into their postmortem process, catches an idempotency gap during review — before it causes an incident — and that specific save becomes the case made to fund expansion to three more teams, rather than a mandate imposed top-down.
- **A shared-resource entry finally gets an owner.** After two unrelated teams both suffer outages traced to the same shared connection-pool proxy, the resilience working group notices neither catalog names it, assigns the platform team as owner, and the next incident's root cause is confirmed against an existing entry within minutes instead of hours.
- **A contract violation gets attributed correctly.** An incident traces to a dependency silently changing its timeout default without notice; because the failure-mode contract was published and version-controlled, the postmortem attributes the incident to the dependency team's undeclared change, not to the consuming team's "insufficient resilience," and the fix is a contract-change review process, not a blame-driven rewrite.
- **Surprise-incident rate as the real signal.** An org reaches 90% catalog coverage but the surprise-incident rate hasn't moved; the retrospective finds most entries are unvalidated guesses from a rushed initial push, and the next two quarters focus on validation coverage instead of new coverage.

## Common Mistakes

- **Centralizing ownership of every service's catalog.** A central team burns out trying to hold context they don't operationally have, and catalogs go stale the moment that team's priorities shift.
- **Mandating full coverage before piloting.** Skipping the pilot means the schema is designed by committee guesswork and gets revised painfully after mass adoption instead of cheaply after one team's experience.
- **Measuring only coverage, never validation or surprise-incident rate.** High coverage with shallow, unvalidated entries looks like success on a dashboard while producing none of the actual resilience benefit.
- **Treating the catalog as a one-time deliverable.** Without a mandatory review trigger tied to architecture change and postmortems, the catalog drifts out of sync with the system within a couple of quarters.
- **Leaving shared-infrastructure failure modes unowned.** No single service team will claim a shared cache or connection pool as "theirs to catalog," so without an explicit assignment this entire category — often the source of the worst cascading incidents — goes undocumented indefinitely.
- **Publishing failure-mode contracts and never reviewing changes to them.** A contract that isn't versioned and reviewed on change is just documentation that quietly goes stale, same as the catalog itself.

---

## Apply it

1. Choose one real service in your org that has caused at least one incident in the past year, and define the outcome measure you'd use to judge whether cataloging its failure modes actually helped (start with `surprise_incident_rate` for that one service).
2. Assign a named owner for the service-level catalog, and separately name the owner for any shared infrastructure it depends on that no single team currently claims.
3. Decompose the rollout into at least three reversible increments (pilot, schema extraction, postmortem integration, expansion) rather than one big-bang mandate, and write the exit condition that moves you from one increment to the next.
4. Draft a one-page failure-mode contract for that service aimed at its actual consumers: declared timeout behavior, and which failure modes are stable versus subject to change.
5. Define the review trigger that would force this catalog to be revisited — tie it to a real event (a new dependency, a postmortem, an architecture review) rather than a calendar reminder alone.

## Verify your work

- The outcome measure is specific and falsifiable (a rate or a percentage with a clear numerator and denominator), not a vague statement like "improved resilience."
- Every entry in the catalog, including shared-infrastructure entries, has a named owning team — no entry is orphaned.
- The rollout plan's exit conditions are concrete enough that someone outside the pilot team could judge whether the pilot succeeded.
- The failure-mode contract is specific enough that a consuming team could design a timeout or circuit breaker directly from it without asking the owning team a follow-up question.
- The review trigger is tied to an event that will actually recur (deploys, postmortems, architecture reviews), not to goodwill or memory.

## Review questions

- Why does centralizing failure-mode catalog ownership in one team tend to fail over time?
- What does the surprise-incident rate measure that catalog coverage alone does not?
- Why should a shared-infrastructure failure mode have an explicitly assigned owner separate from any single consuming team?
- What turns a failure-mode contract into something a consuming team can actually design against, rather than just documentation?
