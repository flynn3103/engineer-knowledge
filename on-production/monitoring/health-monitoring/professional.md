# Health Monitoring — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How do you make a correct liveness/readiness contract the org-wide default for every new and existing service, so that a new team doesn't independently reinvent a broken health check that becomes next quarter's restart-storm incident?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core Concept 1 — Ownership Aligned to Cognitive Load

The predictable organizational failure mode: a central platform or SRE team tries to review and approve every service's health-check implementation individually, burns time it doesn't have holding operational context for hundreds of independently-owned services, and the review queue becomes the bottleneck that teams route around by shipping without review. The split that actually holds distributes ownership by who has the context to get each decision right:

| Layer | Owner | Responsibility |
|---|---|---|
| **Which dependencies are hard vs. soft for this service** | The team that owns the service | Only they know their own request paths well enough to say which dependencies are truly required for every request versus degradable |
| **The shared contract: what liveness must never do, what readiness may do, response shape, timeouts** | A platform or SRE team | Define the org-wide rules once, so every team's implementation is comparable and reviewable by the same checklist |
| **The default implementation teams start from (a base image, framework middleware, or shared library)** | The platform team | Provide a correct-by-default `/healthz` and `/readyz` scaffold so most teams never have to build the liveness/readiness split from scratch |
| **Fleet-wide drift and incident tracking** | SRE or a governance working group | Track which services deviate from the contract, and whether restart-storm or gray-failure incidents correlate with specific deviations |

This split keeps each layer within what its owner can actually sustain: no service team is asked to design the whole liveness/readiness contract from first principles, and the platform team isn't asked to hold per-service context about which dependency is hard versus soft for a service it doesn't operate.

## Core Concept 2 — Decomposing the Rollout Into Reversible Increments

Mandating "every service adopts the contract by end of quarter" produces theater: rushed, unverified compliance applied to hit a deadline rather than to actually prevent the failure modes the contract exists to prevent. Decompose it instead:

1. **Pilot on the service with the most recent incident** — a restart storm, a gray failure, or an outage traced to a health-check gap. Motivation already exists, and a fix is easy to point to as evidence.
2. **Extract the shared contract and scaffold from the pilot**, rather than designing it by committee up front. The pilot reveals which parts of the contract are load-bearing (the liveness-must-be-shallow rule, the readiness-timeout requirement) and which speculative additions nobody actually needs.
3. **Wire the scaffold into the service-creation template** (a cookiecutter template, a shared base image, a service-catalog default) before expanding further, so every *new* service gets the contract for free from day one, rather than needing a retrofit later.
4. **Expand to existing services incrementally**, prioritized by which have the highest request volume or the most dependencies, not by an arbitrary alphabetical sweep — and track adoption as a fraction (services following the contract / total services), not a binary "done."
5. **Only after the contract and scaffold have survived several real onboardings**, treat deviation from it as something governance actively flags — a contract revised after wide adoption is expensive; one revised after three or four real teams' feedback is cheap.

Each step stays independently reversible: if the contract needs a new field (say, an explicit `startupProbe` recommendation for slow-booting JVM services) after the fifth team adopts it, that's a contract revision, not a program failure, because nothing downstream assumed the first version was final.

## Core Concept 3 — Migration, Governance, and Operational Risk

Rolling a health-check contract out across an organization with years of existing, inconsistent services surfaces risk a single pilot doesn't:

- **Legacy services with no dedicated health endpoint at all.** These often default to a bare TCP-connect check from the orchestrator, which only proves a socket accepted a connection — it says nothing about the process's actual state. Migrating them starts with adding a shallow `/healthz` first, as the lowest-risk change, before attempting a real readiness check.
- **A shared base image or middleware library used by many services.** Once dozens of services depend on the same health-check scaffold, a bug in that scaffold (an unintended dependency call added to the shared liveness handler, for instance) can simultaneously break liveness behavior fleet-wide — the shared-infrastructure blast radius the platform team explicitly owns from Core Concept 1.
- **Inconsistent probe configuration across teams.** One team sets `failureThreshold: 1` (a single missed probe restarts the container), another sets `failureThreshold: 10` (a genuinely broken process takes minutes to be noticed). Without a recommended default range in the contract, orchestrator behavior becomes unpredictable across the fleet even when every individual service's check logic is correct.
- **Coordination across teams that don't normally talk.** A service's readiness check calling into another team's internal API as a "hard dependency" creates an undeclared coupling — if the callee team changes their API's latency profile, the caller's fleet-wide readiness behavior changes without either team realizing why. This needs the same kind of explicit contract discipline as any other cross-team dependency.

## Core Concept 4 — Outcome Measures and Exit Conditions

A durable program needs measures that show it's preventing real incidents, not just producing compliant-looking YAML:

```yaml
# Program health dashboard, reviewed quarterly.
metrics:
  contract_adoption: "services using the shared scaffold and passing the contract checklist / total services"
  restart_storm_incidents: "incidents where >1 replica of the same service restarted within the same 5-minute window due to a dependency-check-in-liveness pattern"
  gray_failure_incidents: "incidents where readiness reported healthy but real error rate was elevated for that instance"
  probe_config_variance: "spread of failureThreshold/periodSeconds values across services, vs. the contract's recommended range"
exit_conditions:
  pilot_to_scaffold: "pilot service demonstrates zero restart-storm incidents for one full quarter after adopting the shared scaffold"
  scaffold_to_default: "scaffold has been adopted by at least three independent teams with no required contract revision in the prior quarter"
  program_maturity: "restart_storm_incidents trending toward zero fleet-wide, and contract_adoption > 80% of in-scope services"
```

The number that matters most is `restart_storm_incidents`, not `contract_adoption`. A fleet can reach high nominal adoption — every service has a `/healthz` and a `/readyz` — while several of them still have a dependency check leaking into liveness, because "has the two endpoints" and "the endpoints do the right thing" are different claims. Track incidents attributable to the specific failure modes the contract exists to prevent, and treat a flat or rising incident rate despite high adoption as evidence the contract's checklist itself is missing something, not as a reason to push harder on adoption numbers alone.

## Core Concept 5 — Cross-Team Contracts

Once a health-check pattern is shared across teams, the contract needs the same explicit discipline as an API contract:

- The contract states, explicitly and in one place: what liveness must never do (call anything outside the process), what readiness may do (check declared hard dependencies only, with a required timeout range), the expected response shape, and the recommended `failureThreshold`/`periodSeconds` ranges.
- Every service publishes which dependencies it has declared "hard" for its own readiness check, and that declaration is itself reviewable — a service declaring an internal API call from another team as a hard dependency creates a cross-team coupling that the *other* team should know about, since a latency change on their side now affects this service's fleet-wide readiness behavior.
- A contract change — tightening the required timeout range, adding a new mandatory check — goes through the same review and deprecation-window process as an API breaking change, because for a service team that built its onboarding around the old contract, a silent tightening functionally is one.
- Accountability follows the contract: if a restart storm traces to a service ignoring the "liveness must be shallow" rule, that's the service team's action item; if it traces to a shared scaffold bug affecting many services at once, that's the platform team's.

## Core Concept 6 — Sustained Delivery, Not a Static Rollout

A health-check contract is never "finished" — new services keep appearing, existing services add new dependencies, and shared scaffolds get modified. A sustainable cadence:

- **Enforce the contract at service-creation time**, not just at audit time — a new-service checklist or scaffold generator that includes the correct liveness/readiness split by default means most teams never have the chance to reinvent a broken version.
- **Trigger a review when a service declares a new hard dependency**, the same way an API contract change triggers a consumer review — a newly-declared hard dependency changes that service's blast-radius profile and deserves a quick sanity check against Core Concept 3's cross-team coupling risk.
- **Incident- and drift-driven contract updates as the primary maintenance mechanism**, not a separate "compliance week" nobody prioritizes. A restart-storm postmortem or a probe-config-variance finding is real evidence the contract (or its enforcement) has a gap; a calendar reminder to "review health checks" is not.
- **A program-level retrospective every two quarters** against the outcome measures from Core Concept 4, asking explicitly: is `restart_storm_incidents` actually falling, and if not, is the gap in the contract's content, the scaffold's implementation, or a team that opted out of the scaffold entirely?

---

## Real-World Examples

- **A pilot's fix becomes the case for a scaffold.** A payments-adjacent service that suffered a restart storm from a database check leaking into liveness adopts the corrected pattern; the postmortem's fix becomes the shared scaffold's first version, giving the platform team concrete evidence — not a hypothetical — to justify rolling it out further.
- **A legacy service gets the cheapest safe upgrade first.** A ten-year-old service with only a bare TCP-connect check gets a shallow `/healthz` added as a low-risk first step, deferring a full readiness check with dependency awareness to a later increment, so the migration doesn't stall waiting for a bigger change.
- **A shared scaffold bug is caught before it spreads further.** A platform-team code review catches a change that would have added a Redis call to the shared library's liveness handler, before it ships to the dozens of services that depend on that library — exactly the shared-infrastructure blast radius Core Concept 3 calls out.
- **Adoption looks complete, but the incident rate says otherwise.** An org reaches 85% nominal contract adoption, but `restart_storm_incidents` stays flat; the quarterly retrospective finds several "adopted" services pass the checklist on paper while still burying a dependency check in a custom liveness override — the next revision of the checklist adds an automated static check for exactly that pattern instead of relying on manual review.

## Common Mistakes

- **Centralizing every service's health-check review in one platform team.** That team cannot sustain per-service operational context, and the review queue becomes the bottleneck teams route around.
- **Measuring adoption without measuring incidents.** High nominal adoption with a flat or rising restart-storm rate means the contract's checklist, not the rollout percentage, is what needs attention.
- **Mandating full compliance before piloting.** Skipping the pilot means the contract is designed by guesswork and gets expensively revised after wide adoption instead of cheaply after one team's real experience.
- **Leaving the shared scaffold without a dedicated owner.** A bug introduced into a shared health-check library affects every service that depends on it simultaneously — this needs the same explicit ownership as any other piece of shared infrastructure.
- **Treating cross-team hard-dependency declarations as invisible.** A service quietly declaring another team's API as a hard dependency creates a coupling neither team tracks until an incident reveals it.
- **Running the program as a one-time rollout instead of a maintained contract.** Without a trigger tied to new hard-dependency declarations and a recurring retrospective against real incident data, the contract drifts out of sync with how services actually evolve within a couple of quarters.

## Apply it

1. Pick one real service in your organization that has caused, or narrowly avoided, a restart-storm or gray-failure incident, and define which outcome measure from Core Concept 4 you'd use to judge whether a shared contract actually helps here.
2. Draft a one-page health-check contract: what liveness must never do, what readiness may check, required timeout and threshold ranges, and the expected response shape — aimed at being usable by a team that has never seen it before.
3. Decompose the rollout into at least three reversible increments (pilot, scaffold extraction, service-creation-template integration, expansion), and write the concrete exit condition that moves you from one increment to the next.
4. Identify one place where a service has declared another team's dependency as "hard," and describe the cross-team review that declaration should trigger.
5. Define the recurring trigger (a new hard-dependency declaration, a restart-storm postmortem, a quarterly retrospective) that would force this contract to be revisited, rather than relying on a calendar reminder alone.

## Verify your work

- The outcome measure you chose is specific and falsifiable (a rate with a clear numerator and denominator tied to actual incidents), not a vague statement like "better reliability."
- The contract is specific enough that a team unfamiliar with it could implement a correct `/healthz` and `/readyz` without asking you a follow-up question.
- The rollout plan's exit conditions are concrete enough that someone outside the pilot team could judge whether the pilot succeeded.
- The cross-team coupling you identified names the two teams involved and what review step closes the gap.
- The review trigger is tied to an event that will actually recur (a new dependency declaration, a postmortem, a scheduled retrospective), not to memory or goodwill.

## Review questions

- Why does centralizing every service's health-check review in one platform team tend to fail as the organization grows?
- What does a flat or rising restart-storm incident rate reveal that contract-adoption percentage alone does not?
- Why does a shared health-check scaffold or base image need an explicitly assigned owner separate from any single service team?
- What turns a health-check contract into something a new team can implement correctly without help, rather than just documentation?
