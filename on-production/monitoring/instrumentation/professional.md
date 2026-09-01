# Instrumentation — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How do you roll out an org-wide instrumentation standard across dozens of independently-owned services without a big-bang migration, while proving the standard is actually reducing cardinality incidents and coverage gaps rather than just adding process?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core Concept 1 — From Shared Library to Operating Model

The senior-level concern was designing a shared instrumentation wrapper with the right invariants. The professional-level concern is different in kind: given that wrapper exists, how does an organization of many independently-owned services actually adopt it, keep adopting it as new services are born, and know — with evidence, not confidence — that the adoption is working. This is a durable-delivery problem: instrumentation quality isn't a project with an end date, it's an ongoing property of how the organization builds services, and the operating model has to keep producing that property after the original design team has moved on to other work.

## Core Concept 2 — Aligning Instrumentation Ownership with Team Boundaries

A platform or observability team can own the shared instrumentation *library* — its API, its allowlist mechanism, its default bucket boundaries. It cannot, and should not, own instrumentation *decisions* for every one of 40 services, because that doesn't scale and it removes the local context (this endpoint's real latency profile, this queue's real business-outcome taxonomy) that only the owning team has. The durable split:

- **Platform team owns**: the wrapper library, the naming schema, the cardinality-budget mechanism and its default threshold, the CI check that flags violations, the service-scaffold defaults for new services.
- **Service teams own**: which specific metrics their service emits beyond the defaults, their service's label allowlist contents, responding to their own cardinality-budget alerts, migrating their own call sites off the legacy unwrapped pattern.

This split keeps cognitive load bounded on both sides — a service team doesn't need to understand cardinality-budget internals to get a sane default, and the platform team doesn't need per-service domain knowledge to keep the shared mechanism sound. Cross-team contracts should be explicit and machine-checkable where possible: a CI check that fails a build introducing a metric with a label outside the service's declared allowlist is a real contract; a wiki page saying "please don't do that" is not.

## Core Concept 3 — Decomposing the Migration into Reversible Increments

A 40-service instrumentation migration fails when treated as one big initiative with one due date. Decompose it instead into increments that are each independently valuable, reversible, and observable:

1. **Ship the wrapper library and cardinality-check tooling with zero required adoption.** Value delivered: the tooling exists and can be dogfooded by the platform team's own services first. Reversible: nothing else depends on it yet.
2. **Default new services to the wrapper via the service scaffold**, with existing services untouched. Value: coverage growth becomes automatic going forward without touching legacy risk. Observable: the fraction of services created after date X using the wrapper should be ~100%; track it.
3. **Instrument the existing legacy metrics pipeline to detect and report cardinality/naming violations without blocking anything**, giving every service team visibility into their own current state before being asked to change. Observable: a per-service report of violation count.
4. **Open opt-in migration for existing services, prioritized by measured risk** (services with either the highest current cardinality growth rate or the most recent cardinality-related incident go first, not alphabetically or by team seniority). Reversible: a service can migrate one metric at a time; the old and new patterns can coexist inside one service during transition.
5. **Set an exit condition with a deadline for the long tail**, only after the first four increments have independently proven the tooling and process work — for example, "any service still emitting unbounded-label metrics after this date requires an explicit, time-boxed exception filed with the platform team," rather than an indefinite grace period.

```mermaid
flowchart LR
    A[Ship wrapper, zero adoption] --> B[New services default to wrapper]
    B --> C[Detect-only reporting on legacy services]
    C --> D[Opt-in migration, risk-prioritized]
    D --> E[Deadline for long tail with exception process]
```

Each increment produces observable evidence before the next is greenlit — this is what keeps the initiative reversible: if increment 3's reporting reveals the violation taxonomy is wrong (too many false positives, say), that's caught before opt-in migration starts, not after teams have already been told what to fix.

## Core Concept 4 — Outcome Measures and Exit Conditions

"We rolled out the new instrumentation standard" is not evidence of anything. The professional-level version states measurable outcomes up front and checks them, not just ships:

| Outcome measure | How it's evidenced | Exit condition |
|---|---|---|
| Cardinality incidents (metrics-backend degradation traced to an unbounded label) | Count per quarter, tracked from incident postmortems | Trending down quarter over quarter after rollout, not just "zero this month" (too small a sample to trust) |
| Coverage gaps (services or components with zero RED-style metrics) | Automated scan across the service registry | Percentage of services with full coverage rising toward an agreed target, tracked monthly |
| Naming consistency | Automated check for metric names matching the shared schema, run across all scraped metrics | Percentage of non-conforming metric names decreasing over time, with new services at or near 100% conformance from the scaffold default |
| Migration adoption | Percentage of legacy services using the wrapper vs. raw client-library calls | Rising monotonically post-launch of the opt-in phase; a flat or declining trend means the incentive to migrate isn't real and the plan needs revisiting |

These numbers matter because they're the difference between "the initiative is governance theater" and "the initiative measurably reduced the failure modes it was built to reduce." If cardinality incidents aren't trending down eighteen months after rollout, the honest conclusion is that the operating model needs to change, not that teams need to be reminded again.

## Core Concept 5 — Scenario: Sustained Delivery, Not a Static Target

Six months after the migration plan above launches, a new complication appears: three new services were built by a team acquired via a reorg, already instrumented with a third-party APM's own client library, using entirely different naming and label conventions. This is exactly the kind of sustained-delivery pressure a durable operating model has to absorb without a special-case crisis response each time.

The professional-level answer treats this the same as any other legacy-adoption case, not as an exception requiring new process: the newly-onboarded team's services get scanned by the same detect-only reporting from increment 3, get prioritized in the risk-based queue from increment 4 based on their actual cardinality/coverage numbers (not their org-chart novelty), and inherit the same opt-in migration path and exception process as every other legacy service. The operating model's value is precisely that this doesn't require a new plan — it requires the existing plan to already have room for a service showing up mid-flight.

## Governance, Compliance, and Coordination Risks Worth Naming

- **Compliance-adjacent labels drifting into metrics.** A well-intentioned engineer under deadline pressure adding a customer email or account ID to a label to "make debugging easier" is a data-handling risk as much as a cardinality risk — the platform team's allowlist mechanism should be treated as a policy control, not only a performance control, and reviewed with that framing.
- **Coordination cost of the exception process.** If filing a time-boxed exception becomes bureaucratically expensive, teams will route around the entire standard rather than use the sanctioned escape hatch — the exception process's own friction needs to be monitored as an outcome measure, not assumed benign.
- **Platform team becoming a bottleneck.** If every allowlist addition requires a platform-team review, the platform team can become the single point of delay across 40 service teams; a self-service allowlist mechanism with automated policy checks (rather than manual review) avoids this while keeping the underlying invariant enforced.

## Apply it

1. Write a five-increment rollout plan (mirroring Core Concept 3) for adopting a shared instrumentation wrapper across a set of existing services you specify, stating what value each increment delivers independently and what evidence gates progression to the next.
2. Define the four outcome measures from Core Concept 4's table for your specific scenario, including a concrete numeric or trend-direction exit condition for each — not "improve," but a stated direction and a check interval.
3. Draft the ownership split (platform team vs. service team) as a short, explicit list of responsibilities, and identify one responsibility that is currently ambiguous in your draft — then resolve it.
4. Design the exception process for services that miss the long-tail deadline: what it requires to file, who approves it, and what happens if a service holds an open exception past its own time-box.
5. Simulate the "surprise legacy service" scenario (a newly onboarded team with incompatible existing instrumentation) and show, using your existing plan's risk-prioritization mechanism, where that service lands in the migration queue without inventing new process for it.

## Verify your work

- Each of your five increments states a value delivered on its own and a piece of evidence gating the next increment, not just a date.
- Every outcome measure has a specific direction and cadence (for example "cardinality incidents trending down, reviewed quarterly"), not a vague aspiration.
- Your ownership split resolves at least one ambiguous responsibility explicitly, with a named owner, rather than leaving it implicit.
- Your exception process names an approver and a consequence for an exception outstanding past its time-box, not an open-ended grace period.
- The surprise-legacy-service scenario is absorbed by your existing risk-prioritization mechanism without a new, separate process being invented for it.

## Review questions

- Why is a CI check that fails a build a stronger cross-team contract than a documented convention on a wiki page?
- What specific evidence would tell you, eighteen months in, that the instrumentation rollout is governance theater rather than a working operating model?
- Why should a newly onboarded team's incompatible legacy instrumentation be absorbed by the existing migration plan rather than triggering a special-case process?
- What happens to adoption if the exception process for missing a migration deadline is bureaucratically expensive to use?
