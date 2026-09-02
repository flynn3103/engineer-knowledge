# Choosing the Right Model — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How do you run model selection as an org-wide operating model — an approved model list, an exception process for teams that need something off-list, and a cost/quality review cadence — so individual teams choose well without a central team reviewing every request, and the process survives vendor deprecations and new model releases?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core Concept 1 — Ownership Aligned to Cognitive Load

The predictable failure mode at scale: a central platform or AI-infra team tries to personally review and approve every team's model choice, becomes a bottleneck the moment more than a handful of teams are shipping AI features, and the review queue grows faster than the team can clear it. The split that scales distributes ownership by who actually has the context to make each decision correctly and sustain it:

| Layer | Owner | Responsibility |
|---|---|---|
| **Approved model list** | Platform/AI-infra team | Maintain a small, curated set of models teams can use without individual approval, each tagged with cost tier, context length, modality, and tool-calling reliability from prior internal bake-offs |
| **Model gateway / adapter layer** | Platform/AI-infra team | A single internal interface every team calls through, so swapping a default model or routing around a deprecated one is a configuration change, not a code change in every consuming service |
| **Feature-specific model choice within the approved list** | The team that owns the feature | Runs its own bake-off (middle level) among approved candidates and picks the one that fits its task, cost, and latency needs |
| **Data-classification and residency rules** | Security/compliance | Defines which models and regions are permitted for which data classes (PII, regulated data, public data), independent of any single team's preference |
| **Program health and enforcement** | A governance working group spanning platform, security, and finance | Tracks adoption, exception backlog, cost trend, and deprecation risk across the org; escalates when a team's usage falls out of policy |

This keeps each layer within what its owner can actually sustain: no product team is asked to track every vendor's deprecation calendar or re-litigate a compliance review, and no central team is asked to understand every feature's specific quality requirements.

## Core Concept 2 — The Approved Model List as a Paved Road

An approved model list only works if it's genuinely easier to use than going around it. Each entry carries the information a team needs to skip re-deriving a decision the org has already made:

```text
model_id: claude-sonnet-class-v2
cost_tier: mid
context_length: 200k tokens
modality: text, vision
tool_calling: supported, high reliability (internal bake-off, Q2)
data_classification: approved for PII (region-locked deployment available)
status: current
```

A team building a new feature checks the list first. If an approved entry plausibly fits (right cost tier, right modality, permitted for the data classification involved), it runs its own bake-off among 2-3 approved candidates — no separate compliance or platform review needed, because the list has already pre-cleared those models for that data classification. This is the same leverage as a shared, audited library: the compliance and reliability review happens once, centrally, and every consuming team inherits it.

## Core Concept 3 — Exception Process for Off-List Models

Sometimes no approved model fits — a new task genuinely needs a capability (a modality, a context length, a specific tool-calling behavior) the current list doesn't cover. A lightweight, time-boxed exception process keeps this from becoming either a rubber stamp or a permanent bottleneck:

1. **Team submits a short request**: the task, why no approved model clears the bar (bake-off evidence from the middle-level process, run against the closest approved candidates first), estimated cost and volume, and the data classification involved.
2. **Fast-track vs. full review, based on data sensitivity.** A request involving only public, non-regulated data can be fast-tracked by the platform team alone. A request involving regulated or PII data requires security/compliance sign-off before the exception is granted.
3. **The exception is time-boxed**, not indefinite: the model is approved for a defined evaluation period, after which it's either promoted onto the approved list (if adoption and performance justify it) or sunset, with the requesting team given a migration path back onto an approved candidate.

This prevents two failure modes at once: teams silently going around the list because getting an exception is too slow, and the approved list bloating indefinitely with one-off exceptions that were never actually reassessed.

## Core Concept 4 — Cost and Quality Review Cadence

A quarterly review keeps the program honest about whether it's delivering real outcomes, not just compliance theater:

```yaml
# Program health dashboard, reviewed quarterly.
metrics:
  approved_list_adoption: "requests served by an approved model / total model requests org-wide"
  cost_per_request_trend: "median cost per request, by feature, tracked quarter over quarter"
  exception_backlog: "open exception requests, and median time to resolve one"
  quality_drift: "rubric score on each feature's held-out eval set, re-measured quarterly, versus its score at launch"
  deprecation_response_time: "median time from a vendor deprecation notice to a team's migration completing"
exit_conditions:
  new_model_promoted: "an exception model served real production traffic for its full evaluation window without a quality or cost regression, and at least one other team independently confirms the same result"
  feature_over_provisioned: "a feature using a higher-cost-tier model scores no better on its rubric than an approved lower-cost-tier candidate would, triggering a mandatory re-bake-off before the next budget cycle"
```

`quality_drift` matters because a model's real-world behavior is not static even when nothing in your own system changed — a vendor can silently update a model version behind the same API identifier, and a rubric score measured at launch can quietly stop reflecting current behavior. Re-measuring quarterly against the same held-out set catches this before a user-facing regression does. `cost_per_request_trend` catches the professional-level version of the junior mistake — a feature that was correctly sized at launch but has since been swapped onto a higher tier "for safety" without a corresponding rubric re-check.

## Core Concept 5 — Vendor Deprecations and New Releases

Two events keep happening indefinitely and the operating model has to absorb both without an emergency each time:

- **Vendor deprecation.** A provider announces a model version will stop being served on a fixed date. Because every consuming team calls through the model gateway (Core Concept 1) rather than a vendor SDK directly, the platform team maintains one inventory of which gateway routes point at which model IDs — deprecation response becomes "update the routes and notify the affected teams from the inventory," not "hope every team individually reads the vendor's announcement." A gateway also lets a deprecated route be pointed at a compatible replacement centrally, buying time for teams to re-bake-off before their code has to change at all.
- **New model release.** A new model entering a cost/capability tier is not adopted automatically — a pilot team re-runs the middle-level bake-off against the current champion on their own held-out eval set before anything changes. Only after a pilot confirms a real, measured improvement does the platform team consider promoting the new model onto the approved list for broader use, following the same reversible-increment discipline as any other rollout: one team first, then expand.

## Core Concept 6 — Sustained Delivery, Not a Static Target

A model-selection program has no finish line — it's a cadence, not a project with an end date. One illustrative year:

- **Q1** — establish the approved list and the model gateway; migrate the two highest-volume features onto approved models with documented bake-off evidence.
- **Q2** — a vendor releases a new frontier-class model; a pilot team re-runs its bake-off, confirms a real quality improvement on its held-out set, and the platform team promotes it onto the approved list after that confirmation.
- **Q3** — a vendor announces deprecation of an older model version several teams still route to; the gateway inventory identifies every affected route in minutes, and migration completes ahead of the deprecation date instead of as an emergency the week the old version stops responding.
- **Q4** — the quarterly cost review flags a feature running on a frontier-class model whose rubric score, re-measured, is statistically indistinguishable from a mid-tier approved candidate's — the `feature_over_provisioned` exit condition triggers a mandatory re-bake-off, and the feature moves to the cheaper tier with no quality loss, freeing budget for the next quarter's exception requests.

None of these four events required breaking the operating model to handle — each was absorbed by a mechanism (the gateway, the exception process, the review cadence) that already existed before the event happened.

## Real-World Examples

- **A pilot's measured win funds a wider rollout.** A new mid-tier model release, piloted by one team against their existing held-out set, shows a real quality improvement at a lower cost than their current approved candidate — this concrete, measured result is what justifies promoting the model onto the org-wide approved list, rather than a platform team mandating adoption on the strength of the vendor's own announcement.
- **A gateway turns a deprecation into a routine update instead of an incident.** A vendor announces a model retiring in ninety days; because every team's calls route through the gateway, the platform team's inventory shows exactly which features are affected, and the migration is scheduled and completed weeks ahead of the deadline instead of discovered when calls start failing.
- **An unautomated exception process becomes the actual bottleneck.** A team's off-list request sits unreviewed for weeks because the process depends on a person manually checking a queue; the team quietly starts calling the off-list model anyway without ever getting a review, exactly the shadow-adoption the exception process was meant to prevent — the fix is a defined SLA on exception review time, tracked as part of `exception_backlog`.

## Common Mistakes

- **Centralizing every team's model choice in one platform team.** That team cannot sustain reviewing every feature's specific quality and cost trade-offs at scale, and the review queue becomes the bottleneck to shipping.
- **Publishing an approved list with no data-classification tagging.** Teams then have no way to self-serve the compliance question, and every request effectively needs a manual compliance check regardless of the list's existence.
- **Leaving the exception process without a time box or an SLA.** An unreviewed queue pushes teams toward quietly using off-list models anyway, defeating the purpose of having a list at all.
- **Tracking adoption but never re-measuring quality.** A model can drift or be silently updated by its vendor behind an unchanged API identifier; without a quarterly re-measurement against a fixed held-out set, a regression ships unnoticed.
- **Having no gateway, so every team calls vendor SDKs directly.** Turns a single vendor deprecation into dozens of independent, uncoordinated emergencies instead of one centrally-managed route update.
- **Treating "adoption of the approved list" as the only success metric.** High adoption with no cost or quality review still allows a feature to sit on an over-provisioned, over-priced model indefinitely.

---

## Apply it

1. Draft a minimal approved model list (3-5 entries) for an org you're familiar with, tagging each with cost tier, modality, tool-calling reliability, and the data classifications it's cleared for.
2. Design the exception request process: what a team submits, the fast-track vs. full-review split by data sensitivity, and the time-box for an evaluation period.
3. Define the quarterly review dashboard's metrics, including at minimum adoption, cost trend, and a quality-drift measure, and write the specific exit condition that would trigger a mandatory re-bake-off for an over-provisioned feature.
4. Design the model gateway's inventory: what it needs to record about each team's usage so a vendor deprecation notice can be turned into a list of affected routes within minutes, not days.
5. Walk through the Q1-Q4 scenario in Core Concept 6 for your own org's context and identify which of the four events (adoption, new release, deprecation, cost review) your current process would handle worst today, and why.

## Verify your work

- The approved list entries carry enough information (cost tier, modality, tool-calling reliability, data classification) that a team can self-serve a decision without asking the platform team a question first.
- The exception process has a stated time-box and a fast-track/full-review split, not an open-ended queue.
- The quarterly metrics include a quality-drift measure re-checked against a fixed held-out set, not only an adoption percentage.
- The gateway inventory can answer "which teams and features use model X" without manually surveying every team.
- You can name the specific exit condition that would move a feature off an over-provisioned model, stated as a measurable comparison, not a vague "we should reconsider it sometime."

## Review questions

- Why does centralizing every team's model-selection decision in one platform team tend to fail as the number of teams grows?
- What does a model gateway make possible during a vendor deprecation that direct-to-vendor-SDK calls do not?
- Why is an approved list's data-classification tagging necessary for teams to self-serve a compliance decision?
- What failure does re-measuring quality against a fixed held-out set each quarter catch that adoption tracking alone would miss?
- Why does an exception process without a time-box tend to push teams toward using off-list models without any review at all?
