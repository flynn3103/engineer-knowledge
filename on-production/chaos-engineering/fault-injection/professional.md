# Fault Injection — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How do you run a fault-injection program across many teams, with clear ownership and safety guardrails, that keeps producing measurable resilience gains over a sustained period rather than one good pilot?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

## 1. The Operating Model: Platform Team and Service Teams

A fault-injection program that depends on every service team independently learning `tc`, `iptables`, cgroup limits, and the failure modes of whatever chaos tool is in use does not scale past a handful of enthusiastic early adopters. The operating model that scales splits ownership deliberately:

| Responsibility | Owner |
|---|---|
| Fault-injection tooling and its own reliability | Platform team |
| Approved fault catalog (which fault types are safe to run, at what blast radius, by default) | Platform team |
| Blast-radius policy engine (max % of targets, required approvals, blackout windows) | Platform team |
| Audit trail of every experiment run: who, what, when, approved-by | Platform team |
| Kill switch that disables all active experiments platform-wide | Platform team |
| Hypothesis, steady-state metric, and abort condition for a specific experiment | Service team |
| Their own runbook and on-call awareness for when their experiment runs | Service team |
| Deciding when their service is ready to graduate from staging-only to production experiments | Service team, against platform-defined gate criteria |

This split exists to reduce **cognitive load**: a service team should be able to write a hypothesis and pick from a pre-approved fault catalog without needing to understand kernel-level networking or the chaos tool's internals. The platform team's job is to make the safe path also the easy path — self-service experiment templates, a "chaos-as-code" repository per service where an experiment definition goes through the same review as any other change, and defaults that are hard to misuse (e.g. blast radius defaults to a single canary instance unless explicitly widened).

## 2. Decomposing the Rollout Into Reversible, Observable Increments

Rolling out fault injection as an organization-wide capability is itself a change that needs the same discipline as any other initiative: small, reversible, observable steps rather than a single "chaos engineering launch."

| Phase | Scope | What "done" looks like | Reversibility |
|---|---|---|---|
| 0 — Observability baseline | No faults yet; instrument steady-state dashboards for candidate services | Every pilot service has an agreed steady-state metric with historical data | Trivial — nothing has changed except dashboards |
| 1 — Non-prod pilot | One fault type (process kill), one or two volunteer teams, staging only | Pilot teams have run at least 3 passing experiments with recorded hypotheses | Disable the pilot's access to the platform; nothing outside staging was touched |
| 2 — Catalog expansion | Network and resource faults added; more teams onboard via the self-service template | N teams have working chaos-as-code experiment definitions in staging | Roll back to phase 1's fault catalog if a fault type proves too blunt |
| 3 — Production, tiny blast radius | Approved services run production experiments at low percentage, off-peak, with two-person approval and automatic abort tied to SLO burn-rate | At least one production experiment per approved service has run and auto-aborted correctly at least once in a drill | Platform-level flag disables all production experiments instantly |
| 4 — Scheduled and continuous | Passing experiments become recurring, automated checks | Established, and the natural handoff point to continuous resilience verification rather than one-off fault injection | Any single scheduled experiment can be paused without affecting the others |

The reversibility property that matters most is at the *program* level, not just the experiment level: a single platform-wide kill switch (from §1) means the entire capability can be paused in one action if something about the rollout itself turns out to be unsafe, without needing to hunt down every individual experiment definition across every team.

## 3. Migration, Governance, Operational, and Compliance Risks

| Risk | Description | Mitigation |
|---|---|---|
| False paging | An injected fault's symptoms page on-call as if it were a real incident | Experiment registry auto-annotates any alert firing during an active experiment's window, and pages are suppressed or clearly labeled for the experiment's known blast radius |
| Peak-load collisions | An experiment runs during a high-traffic event (a sales event, a product launch) and amplifies real load-related risk | Platform-enforced blackout windows that reject experiment submissions during declared freeze periods, regardless of team-level approval |
| Regulated-data exposure | A fault targeting a PCI-scoped or otherwise regulated service risks affecting data integrity or availability in a way compliance cares about | A restricted fault catalog and mandatory extra sign-off for any service tagged as regulated-scope, enforced by the policy engine, not by convention |
| Audit and accountability gaps | No record of who approved a production experiment or why | Every experiment run, its approver, its hypothesis, and its outcome are logged immutably and reviewable after the fact |
| The platform itself as a new dependency | The chaos tooling's own downtime or bugs can now affect production systems (see the senior-level discussion of the injection mechanism's own failure modes) | Platform team carries an internal SLA for the tooling's own reliability and for kill-switch response time, and that SLA is itself monitored |

## 4. Outcome Measures and Evidence-Based Exit Conditions

A program is only worth sustaining if it can point to outcomes, not activity. Vague goals like "improve resilience" don't survive a budget review; specific, falsifiable ones do.

| Measure | Target | Evidence |
|---|---|---|
| Tier-1 service coverage | Every tier-1 service has run at least one passing fault-injection experiment per quarter | Experiment registry query, not self-report |
| MTTR trend | Median time-to-recovery for incidents in covered services trends down over two consecutive quarters | Incident-tracking data correlated against experiment history |
| Latent defects found | At least N defects per quarter are found and fixed as a direct result of a fault-injection experiment (not discovered independently) | Linked tickets referencing the experiment that surfaced them |
| Production-eligibility gate | A service is promoted from "non-prod only" to "production-eligible" only after passing the same experiment in staging on 3 separate occasions with no manual intervention | Gate check enforced by the platform, not a judgment call |

Exit conditions are the flip side: a specific fault type or a specific service's production access is *revoked* if it causes two or more false pages in a quarter, or fails to auto-abort correctly in a drill — the same evidence discipline in reverse.

## 5. Cross-Team Contracts and Accountability

The split of ownership in §1 only works if it is written down as an actual contract, not an assumption:

- **Platform team's contract to service teams:** the approved fault catalog behaves as documented, the kill switch works within a stated response time (verified periodically, per the senior-level discussion of testing the mechanism itself), and the audit trail is complete and queryable.
- **Service team's contract to the platform:** no experiment runs in production without a stated hypothesis, steady-state metric, and abort condition on file, and the team owning the service is the team on call when its experiment runs — accountability is not transferable to the platform team.
- **RACI for a production experiment:** service team is Responsible and Accountable for the experiment's design and outcome; platform team is Consulted on blast-radius policy compliance; on-call and any dependent teams are Informed before the experiment window opens.

## 6. Sustained Delivery Scenario

A mid-sized engineering org with roughly 30 service teams rolls this program out over two quarters. Quarter one covers phases 0–2 from §2: five volunteer teams pilot the non-prod capability, refine the self-service chaos-as-code template based on their friction points, and the platform team uses that feedback to fix the rough edges before wider rollout — deliberately not onboarding all 30 teams at once. By the end of quarter one, the template is stable enough that a new team can write their first staging experiment in under a day without platform-team hand-holding, which is the actual signal that the program is ready to scale rather than a fixed calendar date.

Quarter two opens self-service onboarding to the remaining teams, with weekly office hours for questions rather than mandatory synchronous approval for every non-prod experiment — governance effort is reserved for the phase-3 production tier, where two-person approval and blast-radius review remain mandatory. By the end of quarter two, roughly 20 of the 30 teams have at least one experiment in staging, and the 5 pilot teams plus a handful of fast followers have graduated to the production-eligible tier under the gate criteria from §4. The coordination cost stays flat as team count grows because the constant is the *template and the policy engine*, not a person reviewing each new experiment by hand — which is the actual test of whether this operating model, and not just this quarter's rollout, will hold up over the following year.

## Apply it

1. Draft the responsibility table from §1 for your own organization: for each row, name the actual team or role that owns it today (even if the honest answer is "no one yet" — that's useful information).
2. Pick one service and design its phase-0-through-phase-3 path from §2 with specific dates or triggers for graduating between phases, not just "eventually."
3. Write the two contracts from §5 (platform-to-service-team, service-team-to-platform) as short, explicit statements, and check whether either side could currently point to evidence that their half is being honored.
4. Define one outcome measure from §4 that your organization could actually query today (even approximately), and identify what data source or log would need to exist to make it queryable precisely.
5. Identify the single largest governance risk from §3 for your organization specifically, and name the concrete mitigation you'd implement first, given limited time.

## Verify your work

- The responsibility table has a named owner (or an explicit gap) for every row, not blanks left for "figure out later."
- The phase plan for your pilot service has concrete graduation criteria (a number of passing experiments, a specific gate check), not vague milestones like "when ready."
- At least one outcome measure is tied to a real, queryable data source rather than a subjective impression of progress.
- You can state, in one sentence, what would cause a service or fault type to lose production access under your exit conditions.
- A colleague reading your contracts in §5 could independently tell whether the platform team or the service team is accountable for a given failure.

## Review questions

- Why does splitting ownership between a platform team and service teams reduce cognitive load, and what happens if that split isn't written down as an explicit contract?
- What makes a phase-based rollout of the fault-injection program itself reversible, and why does that matter separately from any single experiment being reversible?
- Why is "at least one experiment per quarter" a weaker outcome measure than "MTTR trending down," and what does each actually prove?
- What signal indicates a fault-injection program is ready to scale to more teams, beyond simply reaching a calendar date?
