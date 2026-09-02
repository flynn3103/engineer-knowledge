# Pretrained Models — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How do you run model selection and lifecycle as a durable, org-wide operating model — tracking which product depends on which model version, handling vendor deprecation notices, containing vendor risk, and governing which models get approved or retired — so this doesn't depend on any one team remembering to check?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core Concept 1 — The Failure Mode Without a Model Inventory

At senior level, one team learns to evaluate and roll out a version migration carefully. At professional level, the fact that matters is scale: an organization with a dozen teams calling half a dozen model families across multiple providers has no single person who can answer "which of our services would break if this specific model version were deprecated tomorrow." Without a maintained answer to that question, every deprecation notice becomes a scramble: someone forwards the provider's email, and the org discovers which services depend on the affected model by watching which ones start failing, not by checking a record that already knew.

This is a durable operating-model problem, not a one-time audit. New models release continuously; providers deprecate old versions on their own published schedules; teams adopt new models without necessarily telling anyone else. A model inventory has to be maintained the same way a service registry or a dependency-tracking system is — continuously, with an owner, not produced once for an audit and left to rot.

## Core Concept 2 — Ownership Aligned to Cognitive Load

The same organizational failure that hits any centralized-review model hits this one if it's designed wrong: a central AI platform team trying to personally approve every model call in every service becomes a bottleneck the moment more than a handful of teams are shipping LLM-backed features. The split that scales:

| Layer | Owner | Responsibility |
|---|---|---|
| **Approved model list** | AI platform team | Maintain the current set of approved models/versions per use-case category (e.g., "approved for user-facing chat," "approved for internal completion tasks"), each with a documented rationale |
| **Model inventory (who depends on what)** | Each product team, enforced by tooling | Register which service uses which model version, kept current via a required field in deploy config rather than a manually maintained spreadsheet |
| **Vendor relationship and deprecation tracking** | AI platform team | Track every provider's published deprecation timeline for models currently in the approved list, and own the calendar of upcoming sunset dates |
| **Migration execution and evaluation** | The team that owns the affected service | They have the context on their own golden prompt set and downstream integrations — the senior-level process from the previous guide is executed by them, not for them |
| **Governance and risk review** | A working group spanning platform, security, and product leads | Approves additions/removals from the approved list, reviews vendor concentration risk, and escalates when a team is behind on a mandatory migration |

This mirrors how a platform team owns golden base images while application teams own their own Dockerfile layers: the platform owns the paved road and the calendar; the team that knows its own service owns the actual migration work.

## Core Concept 3 — A Model Inventory That's Enforced, Not Requested

A spreadsheet that teams are asked to update voluntarily goes stale within a quarter. The inventory needs to be a byproduct of something teams already have to do, not an extra step:

```yaml
# Required field in each service's deployment config —
# the inventory is derived from this, not maintained separately.
model_dependency:
  service: support-bot-api
  provider: anthropic
  model: claude-sonnet-4-5
  use_case_category: user-facing-chat
  owning_team: support-eng
  last_migration_eval_date: 2026-06-01
```

A CI check that fails a deploy if `model_dependency` is missing or references a model not on the current approved list turns the inventory into something that's true by construction, not something that's true if everyone remembered to update it. The inventory answers "which services use this model" by querying deployed config, not by asking teams to self-report.

## Core Concept 4 — Handling a Deprecation Notice as a Managed Process, Not a Fire Drill

Every major provider publishes deprecation timelines and sunset dates for specific model versions — this is a real, routine, publicly documented practice across the industry, not an edge case to plan around only after it happens once. The managed version of receiving one:

1. **The deprecation date lands on the platform team's tracked calendar** the moment it's published, not when a team notices their service failing.
2. **The inventory (Core Concept 3) is queried for every service on the affected model**, producing an exact list of owning teams — not a guess.
3. **Each owning team is notified with a concrete deadline** that leaves real time for the senior-level evaluation-and-rollout process (golden set, shadow comparison, canary, staged rollout) — not the provider's sunset date itself, which should be treated as the hard deadline the internal deadline is padded ahead of.
4. **The governance working group tracks migration completion across all affected teams** as a shared dashboard, so a team quietly falling behind is visible before the deadline, not after.

The difference between this and a fire drill is entirely in step 1 and step 2 existing *before* the notice arrives — a calendar with nothing tracked on it and an inventory that has to be reconstructed from scratch both turn a routine, expected event into an emergency.

## Core Concept 5 — Vendor Risk

Depending on one provider for every model an org uses concentrates several distinct risks that are worth naming separately, because they need different mitigations:

- **Single-provider outage blast radius** — if every LLM-backed feature across the org calls one provider and that provider has an outage, every feature degrades simultaneously. Mitigation: for the highest-criticality features, maintain a validated fallback to a second provider's model, not necessarily used by default, but evaluated and ready to route to.
- **Pricing changes** — per-token pricing can change; an org with no visibility into aggregate spend by model discovers a pricing change only in a bill, not in a decision. Mitigation: the inventory in Core Concept 3 doubles as the basis for tracking cost by model and by service, so a pricing change's impact can be estimated before it lands, not after.
- **Forced migration under a compressed timeline** — a provider deprecating a model faster than an org's normal evaluation cycle can absorb. Mitigation: the approved-model list should bias toward models with a track record of reasonable, well-communicated deprecation windows, and the governance group should factor this into approval decisions, not just raw capability.
- **Capability or policy shifts outside the org's control** — a provider changing a model's behavior (tightening or loosening refusal behavior, for instance) between versions in ways that affect an approved use case. Mitigation: the senior-level golden-set comparison process, run as a standing practice rather than a one-off, is what actually catches this.

None of these argue for avoiding closed/API-only providers altogether — for most orgs, the operational and capability trade-off in the middle-level guide still favors using one for at least some features. They argue for treating vendor concentration as a tracked, deliberate risk rather than an unexamined default.

## Core Concept 6 — Governance for Adding and Retiring Approved Models

The approved-model list needs the same discipline as any other list that other teams build against without asking permission each time:

- **Adding a model** requires the requesting team (or the platform team, proactively) to document: what use-case category it's approved for, what evaluation was run to justify approval, and who owns tracking its lifecycle going forward.
- **Retiring a model** — whether because of a provider deprecation, a governance decision to consolidate onto fewer approved options, or a finding that a model is underperforming its use case — goes through the same inventory query as Core Concept 4, with a deadline and a tracked migration, not a silent removal that breaks a team's next deploy.
- **A version bump within an already-approved family** (moving from one Claude, GPT, Llama, or other version to the next) is not automatically re-approved — each new version is evaluated on its own, per the senior-level process, even if the family itself is already trusted.

## Core Concept 7 — Outcome Measures and Exit Conditions

```yaml
# Program health dashboard, reviewed quarterly.
metrics:
  inventory_coverage: "services with a valid model_dependency record / total LLM-backed services"
  deprecation_lead_time: "median days between an internal migration deadline being set and the provider's actual sunset date"
  migration_completion_rate: "teams that completed migration ahead of their internal deadline / teams notified"
  vendor_concentration: "% of total LLM request volume on the single largest provider"
exit_conditions:
  inventory_trustworthy: "inventory_coverage > 95%, enforced by CI rather than manual reporting"
  deprecation_handling_mature: "at least one full deprecation cycle handled with zero services missing their internal deadline"
```

`migration_completion_rate` is the measure that actually proves the operating model works, the same way patch latency proves a golden-image program works rather than adoption percentage alone: an org can have a beautifully maintained inventory and still have every team miss their migration deadline if the notification and evaluation support around Core Concept 4 isn't real. Track completion against internal deadlines specifically — hitting the provider's hard sunset date is passing, not succeeding, since it means no margin existed for a problem found during evaluation.

## Core Concept 8 — Sustained Delivery, Not a Static Target

This program has no finished state. New models release on an ongoing basis, existing ones get deprecated on an ongoing basis, and new teams keep adopting LLM features that need to enter the inventory from day one rather than being retrofitted in after an incident. A sustainable operating cadence:

- **New services onboard with a required `model_dependency` field from their first deploy**, enforced by the same CI check that keeps the inventory trustworthy — not an opt-in step a team has to remember.
- **The deprecation calendar is checked on a standing schedule** (not only when a provider email arrives) against the current approved list, since a provider's own published roadmap can name future sunset dates well ahead of the formal notice.
- **A quarterly governance review** looks at the outcome measures from Core Concept 7 and asks explicitly: is migration completion rate improving, and if a team keeps missing internal deadlines, is the bottleneck their capacity, an evaluation process that's too slow, or a deadline that wasn't padded enough ahead of the real sunset date.

---

## Real-World Examples

- **A deprecation notice becomes a two-hour task instead of a two-week scramble.** A provider announces a sunset date for a model version; querying the inventory immediately produces the exact list of six affected services and their owning teams, and each team receives a deadline padded well ahead of the real sunset date — because the inventory and the calendar both already existed before the notice arrived.
- **A CI-enforced inventory catches a silent adoption.** A team quietly starts calling a model that was never added to the approved list, discovered not by an audit but by their next deploy failing the CI check that validates `model_dependency` against the current approved set — the gap is caught before it becomes a governance blind spot, not after.
- **High inventory coverage doesn't prevent a missed deadline, and the retro finds the real bottleneck.** An org has 98% inventory coverage but one team still misses their internal migration deadline; the quarterly review finds the cause is that their golden-prompt-set evaluation process (senior-level work) was never actually built for their service, so migration deadline notification landed on a team with no ready process to execute it — the fix is investment in their evaluation tooling, not a stricter deadline.

## Common Mistakes

- **Maintaining the model inventory as a manually updated spreadsheet.** Goes stale within a quarter; enforce it through deploy-time tooling instead.
- **Centralizing every model-call review in one platform team.** Becomes the actual bottleneck once more than a handful of teams are shipping LLM features — split ownership by who has the context, per Core Concept 2.
- **Treating a provider's deprecation notice as the first time the org learns about the timeline.** Providers publish roadmaps and sunset dates ahead of the formal notice; a standing calendar check catches this earlier.
- **Measuring only inventory coverage, never migration completion rate.** A complete inventory with no ready evaluation process behind it still produces missed deadlines under pressure.
- **Re-approving an entire model family instead of evaluating each new version.** A version bump within a trusted family can still shift behavior enough to break a downstream integration, per the senior-level guide.
- **Concentrating all LLM traffic on a single provider with no evaluated fallback for the highest-criticality features.** Turns a single provider's outage into an org-wide feature outage with no ready alternative.

---

## Apply it

1. Design the `model_dependency` record structure you'd require in deploy config for services at your organization (or a realistic hypothetical one), and the CI check that would fail a deploy referencing an unapproved model or missing the record entirely.
2. Draft the approved-model list format: use-case categories, which models are approved for each, and what evaluation evidence justified each approval.
3. Write the deprecation-handling runbook: who owns the calendar, how the affected-service list gets generated, and how much lead time an internal deadline should have ahead of a provider's published sunset date.
4. Define your `migration_completion_rate` metric precisely (numerator and denominator) and the exit condition that would tell you the program is mature enough to trust.
5. Name one vendor-concentration risk specific to your (or a realistic hypothetical) org's current model usage, and the concrete mitigation you'd put in place for the single highest-criticality feature affected.

## Verify your work

- The inventory's coverage is measured and enforced by tooling, not by asking teams to self-report.
- The deprecation runbook names a specific owner for the calendar and a specific lead-time buffer ahead of a provider's sunset date, not an open-ended "we'll handle it when it comes up."
- Your `migration_completion_rate` metric has a clear numerator and denominator and is measured against internal deadlines, not the provider's hard sunset date.
- You can name a specific service and a specific mitigation for single-provider outage risk, not a general statement that "we should diversify eventually."
- The approved-model list distinguishes model families from specific versions, and your governance process re-evaluates each new version rather than assuming family-level trust carries forward.

## Review questions

- Why does a manually maintained spreadsheet fail as a model inventory, and what makes a deploy-time CI check a more durable alternative?
- What specifically turns a provider's deprecation notice from a fire drill into a routine, managed process?
- Why is migration completion rate a better indicator of program health than inventory coverage alone?
- Name two distinct vendor-concentration risks and explain why they need different mitigations.
- Why should a new version within an already-approved model family still go through its own evaluation before being trusted in production?
