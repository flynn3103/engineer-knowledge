# CI/CD Pipelines — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How do you run pipeline-as-code as a durable, org-wide platform — with clear ownership between a platform team and product teams, governance over secrets and provenance, and measurable delivery outcomes — instead of each team hand-rolling and maintaining its own brittle pipeline?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

*A senior-level architecture gets the invariants right for one well-designed pipeline template. An operating model keeps those invariants holding two years later, after forty more services have onboarded, three security incidents have been investigated, and the person who designed the original template has moved to a different team.*

---

## Core Concept 1 — Ownership Aligned to Cognitive Load

The most common organizational failure in CI/CD is a platform team trying to own every service's pipeline correctness directly — approving every YAML change, debugging every team's flaky test. It doesn't scale, because that team doesn't own the application logic and can't keep pace with every service's release cadence. The split that holds:

| Layer | Owner | Responsibility |
|---|---|---|
| **Pipeline template (stages, gates, security scanning, artifact signing)** | Platform / developer-experience team | Maintain the shared, reusable pipeline definition every service consumes; patch it when a vulnerability or a better practice emerges |
| **Service-specific pipeline configuration (which template version, which tests, which environments)** | The team that owns the service | Keep their own test suite meaningful and green; choose when to adopt a new template version |
| **Secrets and credential issuance** | A platform security function, via a centralized secrets manager | Issue, rotate, and audit credentials the pipeline uses; no team manages its own long-lived cloud credentials by hand |
| **Cross-org policy enforcement (required gates, artifact signing, audit retention)** | Platform team, enforced mechanically in the shared template | Make the senior-level invariants non-optional — a pipeline that skips a required scan should fail to run, not merely generate a warning |

This split keeps no team holding more context than its cognitive load supports: the platform team understands pipeline mechanics and security posture across the fleet; each product team understands its own service's actual risk and test needs. Neither team needs to fully understand the other's domain to do its own job well.

## Core Concept 2 — Decomposing the Initiative Into Reversible Increments

Rolling out a standardized pipeline platform to an entire organization as a single mandate ("every service migrates to the new template by end of quarter") produces the familiar failure of any rushed migration: services technically comply by copying the template and immediately diverging from it, defeating the entire point of standardization. Decompose it instead:

1. **Pilot with one or two services that already have engaged, willing teams** — not the riskiest or most complex service in the organization, so the platform team can prove the template works before it has to survive a hard case.
2. **Extract the required gates from what the pilot actually needed**, not from a design document written in isolation — a required security scan that produces false positives constantly on real code will get suppressed by every future adopter unless the pilot surfaces and fixes that first.
3. **Publish the template as a versioned, reusable workflow** with clear adoption instructions, and integrate template-version tracking into the platform team's own visibility tooling — so "who's on the current template" is a query, not a survey.
4. **Expand cohort by cohort**, prioritizing services with the clearest pain (the most hand-rolled, least-audited pipelines first), and track adoption as a coverage ratio, not a binary "migrated."
5. **Only after several cohorts succeed**, consider making the new template mandatory for new services by default, while giving existing services a scheduled, tracked migration window rather than an abrupt cutover.

Each step is reversible: if the pilot reveals the required scan needs a different tool, that's a template revision before wide adoption, not a rollback of a completed migration.

## Core Concept 3 — Migration, Governance, Operational, Compliance, and Coordination Risk

- **Legacy hand-rolled pipeline backlog.** Older services often have pipelines built ad hoc, years before any shared template existed — inconsistent gates, unclear secret handling, sometimes a manually-triggered deploy script nobody has touched in months. Migrating these requires a deliberate, tracked backlog, not an assumption that teams will get to it "eventually."
- **Secrets governance across a growing fleet.** As services multiply, credential sprawl (Core Concept 3 of the senior level) becomes an organizational risk, not just a technical one. A centralized secrets manager with mandatory rotation and per-pipeline scoped access needs an owning team and a real enforcement mechanism — a policy that says "don't hardcode secrets" without a technical gate blocking it is not governance, it's a suggestion.
- **Third-party action and plugin vetting at scale.** A shared pipeline platform used by many teams becomes an attractive target — a single compromised or malicious action reused across the fleet has a far larger blast radius than one team's isolated mistake. This needs a standing review process for new dependencies entering the shared template, with an owning security function, not an ad hoc check the one engineer who happened to notice performs.
- **Compliance and audit requirements for release evidence.** Where deployments feed into compliance obligations (change-management records, SOC2-style controls, regulatory audit trails), the pipeline's audit lineage must be complete and queryable on demand — a trail that technically exists but requires reconstructing history from several disconnected systems fails an audit just as surely as no trail at all.
- **Coordination cost for a shared runner/compute fleet.** When many teams' pipelines compete for the same build infrastructure, contention (queue time, resource starvation during a peak release window) becomes a shared-tenancy problem that needs explicit capacity planning and prioritization policy — without an owner, the team that complains loudest gets prioritized, which is not a policy.

## Core Concept 4 — Outcome Measures and Exit Conditions

```yaml
# Pipeline platform health dashboard, reviewed quarterly by the platform team.
metrics:
  deployment_frequency: "successful production deploys per service per week (DORA)"
  lead_time_for_changes: "median time from commit merged to running in production (DORA)"
  change_failure_rate: "percentage of production deploys requiring a rollback or hotfix (DORA)"
  time_to_restore_service: "median time from a failed deploy to restored service (DORA)"
  template_adoption_coverage: "services on a supported template version / total services"
  required_gate_bypass_count: "count of any deploy that occurred outside the standard pipeline path"
exit_conditions:
  pilot_to_expansion: "pilot services sustain deployment_frequency and change_failure_rate at or better than their pre-migration baseline for one full quarter"
  program_maturity: "template_adoption_coverage above 90%, and required_gate_bypass_count at zero for two consecutive quarters"
```

`required_gate_bypass_count` matters as much as the four DORA metrics — an organization can show excellent deployment frequency and low change failure rate while a growing number of releases quietly route around the pipeline entirely. Any nonzero bypass count deserves the same attention as a change-failure-rate spike, because it means the other metrics are being measured against an incomplete picture of how software actually reaches production.

## Core Concept 5 — Cross-Team Contracts and Accountability

Formalize the relationship between product teams and the platform team the same way an API contract is formalized between services:

- **Product teams commit to:** keeping their own test suite meaningful and green as a condition of using the shared template's fast-path promotion, and never introducing a deploy path that bypasses the standard pipeline — even temporarily, even for an emergency, without going through the platform team's documented break-glass procedure.
- **The platform team commits to:** patching the shared template promptly when a vulnerability or gate weakness is found, communicating breaking template changes with a migration window rather than a silent update, and keeping template-version adoption visible to every consuming team without them having to ask.
- **The security function commits to:** rotating and auditing pipeline credentials on a fixed cadence, and reviewing new third-party pipeline dependencies within a stated turnaround time so teams aren't incentivized to route around the review out of impatience.
- **Accountability follows the contract, not the org chart.** A production incident traced to a bypassed gate is the responsible product team's action item to fix their process; an incident traced to a vulnerability in the shared template itself is the platform team's action item; a credential leak traced to a missed rotation is the security function's action item.

## Core Concept 6 — Sustained Delivery, Not a Static Target

The platform never reaches a finished state — services keep onboarding, the threat landscape keeps changing, and the template has to keep evolving without breaking what already depends on it:

- **Quarterly platform review**, checking the outcome measures from Core Concept 4 against the exit conditions — including `required_gate_bypass_count`, which is often the first sign the operating model is eroding even while the DORA numbers still look healthy.
- **A continuous template-patch pipeline** of its own — the shared template is itself software with its own build/test/release cycle, versioned and rolled out to a pilot cohort before wide adoption, exactly as Core Concept 2 of the senior level describes for any pipeline logic change.
- **A standing backlog for legacy pipeline migration**, tracked with the same visibility as any other technical debt, rather than a one-time project that quietly stalls once the original sponsor moves on.
- **A mandatory review trigger on any new third-party dependency or major architecture change** (a new deploy target, a new cloud provider, a new compliance obligation) that reopens the template's security review before the change ships broadly, not after an incident surfaces the gap.

---

## Real-World Examples

- **A pilot earns the mandate instead of receiving one.** Two willing teams pilot the new shared template, and the pilot surfaces that the platform team's proposed security scan produces frequent false positives on one team's testing framework; the scan gets tuned before wide rollout instead of being silently suppressed by every future adopter.
- **A bypass count catches what the DORA dashboard missed.** An organization's deployment frequency and change failure rate both look healthy for two quarters, but the newly tracked `required_gate_bypass_count` reveals a growing pattern of "emergency" deploys routing around the pipeline for one team — prompting a review of why their standard path is too slow for their actual incident-response needs, and a fix to the pipeline rather than continued bypassing.
- **A shared runner fleet finally gets a capacity policy.** After a high-traffic release week where several teams' deploys queued for over an hour behind a single team's resource-heavy build, the platform team introduces prioritization policy and dedicated capacity for time-sensitive deploys — closing a coordination gap that had been informally "whoever complains loudest" for months.

## Common Mistakes

- **Mandating full migration before piloting.** Skipping the pilot means required gates get designed in isolation and painfully revised after wide adoption instead of cheaply after one or two teams' real experience.
- **Tracking DORA metrics without a gate-bypass metric.** An organization can look like it's delivering safely and quickly while an increasing share of real releases quietly avoid the pipeline's protections entirely.
- **Treating the shared template as a finished deliverable.** Without its own patch cadence and pilot-first rollout discipline, the template accumulates the same risk (breaking every consumer at once) it exists to prevent for application code.
- **Leaving legacy hand-rolled pipelines as someone else's problem indefinitely.** Without a tracked backlog and an owning function, the riskiest, least-audited pipelines in the organization are often the oldest ones, and they stay that way the longest.
- **Letting a "just this once" break-glass deploy become routine.** Without a real accountability trail on bypasses, the exception becomes the norm for whichever team finds the pipeline's standard path too slow, and the audit trail quietly develops a permanent hole.

## Apply it

1. For your organization (or a plausible one), define the ownership split across platform team, product teams, and a security function for pipeline template maintenance, service-specific configuration, and secrets management — name who owns each.
2. Draft the outcome-measure dashboard for a pipeline platform, including at least one metric beyond the four DORA keys (such as `required_gate_bypass_count` or `template_adoption_coverage`), with a concrete exit condition for moving from pilot to expansion.
3. Decompose a rollout of a new shared pipeline template into at least four reversible increments (pilot, gate extraction, publication, cohort expansion), stating what would trigger moving from one increment to the next.
4. Draft the cross-team contract for your platform: what product teams commit to, what the platform team commits to, and what the security function commits to, in one page.
5. Identify one category of migration, governance, or coordination risk from Core Concept 3 that is currently unmanaged in your organization, and name a specific first step to assign it an owner.

## Verify your work

- The ownership split is specific enough that a new engineer could correctly guess who to contact for a template change versus a service-specific test failure, without asking.
- The dashboard includes a gate-bypass or equivalent trust metric, not just the four DORA keys, with a stated numeric or ratio-based exit condition — not a vague aspiration.
- Each increment in the rollout plan has a concrete trigger for advancing to the next one, and the plan does not assume a single all-at-once cutover.
- The cross-team contract is specific enough that a product team could state, without asking, exactly what they must do to keep using the platform's fast-path promotion.
- The identified unmanaged risk has a named first step and a plausible owner, not just a description of the problem.

## Review questions

- Why does concentrating pipeline-correctness ownership in a single platform team fail to scale as the number of services grows?
- Why is a required-gate-bypass count as important a metric as the four DORA keys for judging a pipeline platform's health?
- What risk does a shared, centrally-owned pipeline template introduce that fully independent per-service pipelines do not?
- What turns a cross-team pipeline contract into something a product team can act on, rather than a policy document nobody rereads?
