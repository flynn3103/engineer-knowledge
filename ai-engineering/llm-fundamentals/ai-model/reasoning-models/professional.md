# Reasoning Models — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How do you run "when is reasoning-mode spend justified" as a durable, org-wide operating model — one that measures whether the premium is actually earning its keep, governs which product surfaces may default to it, and keeps working as the underlying models themselves keep improving?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core Concept 1 — Ownership Aligned to Cognitive Load

The predictable failure mode at org scale: every product team independently decides whether their feature should call a reasoning model, with no shared measurement of whether the premium is worth it and no shared budget discipline — some surfaces silently overspend, others silently under-deliver quality, and nobody has a comparable number across teams to know which is which. The split that scales distributes ownership by who actually has the context to make and sustain each decision:

| Layer | Owner | Responsibility |
|---|---|---|
| **Routing infrastructure, budget enforcement, streaming/timeout plumbing** | Platform / AI infrastructure team | Build and operate the shared router, cost caps, and fallback mechanisms from the senior level once, so no product team reimplements timeout and cap handling independently |
| **Which surfaces default to reasoning mode, and the UX around it** | The product team owning that surface | They know their users' latency tolerance, their task's actual compounding-error profile, and their feature's tolerance for a fallback answer |
| **Quality-per-dollar measurement methodology and the shared eval harness** | A cross-functional AI evaluation function (may overlap with an existing eval/observability team) | Defines how "is reasoning mode worth it here" gets measured consistently, so teams aren't inventing their own ad hoc justification each time |
| **Policy: who may enable reasoning-mode-by-default, budget ceilings, review cadence** | A governance group spanning platform, AI evaluation, and product | Tracks org-wide adoption and spend trends, approves new surfaces defaulting to reasoning mode, and re-reviews existing ones on a schedule |

This split keeps each layer within what its owner can actually sustain: no product team is asked to build its own cost-cap infrastructure from scratch, and no central team is asked to understand every surface's specific UX and latency tolerance.

## Core Concept 2 — Measuring Quality-per-Dollar

The central org-level question is not "does reasoning mode produce better answers" — on compounding-error tasks, it usually does — but **"is the quality delta, at this org's actual traffic volume and actual task mix, worth the cost delta?"** That's a comparison, not a fact about the model:

```yaml
# Quality-per-dollar comparison, run per candidate surface before approving
# reasoning-mode-by-default, and re-run on the review cadence (Core Concept 6).
comparison:
  surface: "scheduling-assistant"
  sample: "200 representative production queries, stratified by observed complexity"
  standard_model:
    task_success_rate: "<measured against the surface's existing eval harness>"
    median_cost_per_request: "<measured>"
  reasoning_model:
    task_success_rate: "<measured against the same harness>"
    median_cost_per_request: "<measured>"
  quality_delta: "reasoning success rate − standard success rate"
  cost_delta: "reasoning cost − standard cost"
  verdict: "worth it if quality_delta, multiplied by this surface's traffic volume and the cost of a wrong answer to the business, exceeds cost_delta at that volume"
```

Two things make this different from a one-time benchmark check. First, it uses the surface's *actual* production query distribution, not a generic benchmark — a surface where "hard" queries are rare gets a different verdict than one where they're common, even with an identical model comparison. Second, it's explicitly a comparison against the standard model *available today*, which is why this needs a review cadence (Core Concept 6) rather than a one-time sign-off — the standard model of six months from now is not the standard model this comparison was run against.

## Core Concept 3 — Decomposing Rollout Into Reversible Increments

Mandating "every eligible surface defaults to reasoning mode by end of quarter" produces the same theater any top-down infrastructure mandate produces: surfaces switched to hit a deadline rather than because the quality-per-dollar comparison actually supported it. Decompose instead:

1. **Pilot on one surface with the clearest compounding-error profile** — a task where the middle-level routing rule would send nearly all traffic to reasoning mode anyway, so the pilot's quality-per-dollar case is as unambiguous as possible.
2. **Run the Core Concept 2 comparison on that pilot's real traffic**, not a synthetic benchmark, and require a concrete, positive verdict before calling the pilot successful.
3. **Extract the shared routing, streaming, timeout, and cap infrastructure from what the pilot needed**, rather than platform building it speculatively ahead of any real usage.
4. **Expand to additional surfaces one at a time**, each requiring its own quality-per-dollar comparison — approval is per-surface, not a blanket policy extended to every team automatically.
5. **Track adoption as a fraction of eligible surfaces with a positive, current quality-per-dollar verdict** — not a raw count of surfaces using reasoning mode, which says nothing about whether the spend is justified.

Each step stays reversible: a surface whose comparison verdict turns negative on a later review (Core Concept 6) reverts to standard-model routing, and that's a normal outcome of the policy working, not a program failure.

## Core Concept 4 — Migration, Governance, and Compliance Risk

Running this across many teams and an evolving set of vendor models surfaces risk a single pilot doesn't:

- **Reasoning-trace exposure risk.** A surface that shows users a raw reasoning trace (or logs it somewhere reachable by a support or compliance workflow) carries the risk described at senior level — a trace that looks authoritative but isn't guaranteed faithful — at organizational scale. This becomes a real compliance and trust question the moment a regulated or customer-facing surface is involved: does showing the trace imply a guarantee the org isn't actually able to back?
- **Runaway spend at aggregate scale.** Senior-level per-request and per-user caps prevent single-request and single-account cost blowups; at org scale, the equivalent question is whether *aggregate* reasoning-mode spend across all approved surfaces is tracked against a budget, so a dozen individually-capped surfaces don't collectively exceed what finance approved.
- **Vendor and model-version drift.** OpenAI's o-series, Claude's extended thinking, and DeepSeek-R1 are all actively evolving — a new model version can shift the quality-per-dollar comparison for every surface using it, in either direction, without any change on the org's side. A policy that doesn't have a trigger tied to vendor model updates is a policy that goes stale silently.
- **Uneven surface eligibility.** Approving reasoning-mode-by-default for a customer-facing, regulated surface (e.g., anything touching financial or medical decisions) carries different compliance weight than approving it for an internal tooling surface — governance needs different bars for different surface categories, not one blanket approval process.

## Core Concept 5 — Outcome Measures and Exit Conditions

```yaml
# Program health dashboard, reviewed on the cadence from Core Concept 6.
metrics:
  eligible_surfaces_with_positive_verdict: "surfaces defaulting to reasoning mode with a current, positive quality-per-dollar verdict / total surfaces defaulting to reasoning mode"
  aggregate_reasoning_spend: "total reasoning-token cost across all approved surfaces, tracked against the approved org budget"
  fallback_and_timeout_rate: "fraction of reasoning calls hitting the senior-level timeout or cost cap, per surface"
  quality_delta_trend: "quality-per-dollar verdict trend per surface, review over review"
exit_conditions:
  pilot_to_expansion: "pilot surface's quality-per-dollar comparison shows a positive verdict on real production traffic, and the shared routing/cap/streaming infrastructure operates the pilot without platform-team intervention"
  surface_revocation: "a surface's quality-per-dollar verdict turns negative on a scheduled review — because a cheaper standard model closed the gap, or because the surface's real traffic mix shifted away from compounding-error tasks — and the surface reverts to standard-model routing"
```

The metric that matters most is `eligible_surfaces_with_positive_verdict`, not raw adoption count — an org can have many surfaces defaulting to reasoning mode while several of them would fail today's comparison if re-run, because nobody re-ran it since the standard model improved. Track the positive-verdict fraction as the real signal of whether the program is delivering what it exists for, not adoption alone.

## Core Concept 6 — Review Cadence: Models Keep Evolving

The single most important professional-level fact about this whole topic: **a standard model six months from now may match today's reasoning model on tasks that currently require it.** Reasoning-model releases and standard-model releases both keep happening, and the gap that justified a surface's reasoning-mode default today is not guaranteed to still exist at any future point. A policy that treats "reasoning mode approved for this surface" as a permanent decision goes stale the first time a vendor ships a materially better standard model.

The operating model needs an explicit cadence, not an implicit "revisit if someone remembers":

- **A scheduled re-review per approved surface** (for example, quarterly) that reruns the Core Concept 2 comparison against whatever standard and reasoning models are current at that time — not the models that were current when the surface was first approved.
- **An event-triggered re-review** independent of the schedule, fired by a new model release from any vendor in active use (a new o-series model, a new Claude extended-thinking version, a new DeepSeek-R1 release, or any standard model that claims to close the gap on multi-step tasks) — the schedule catches drift the org wasn't watching for; the trigger catches drift the org was.
- **A documented revocation path**, not just an approval path — Core Concept 5's `surface_revocation` exit condition should be a normal, expected outcome logged and communicated, not an exception requiring special justification to invoke.

## Core Concept 7 — Cross-Team Contracts

Once multiple product teams depend on shared routing, cap, and streaming infrastructure, and multiple surfaces depend on a shared measurement methodology, formalize the relationship the way an internal API is formalized:

- The governance group publishes the quality-per-dollar comparison methodology (Core Concept 2) as a fixed, versioned process — a team requesting reasoning-mode-by-default for a new surface runs the same comparison every other approved surface ran, not an ad hoc justification.
- The platform team's shared infrastructure (routing, caps, streaming, fallback) publishes a support contract the same way a golden base image would: which capabilities are current, what a breaking change to the shared router's interface requires (advance notice to consuming teams), and who owns an incident when the shared cap-enforcement layer fails.
- Accountability follows the contract: if aggregate spend exceeds budget because the shared cap-enforcement infrastructure had a gap, that's the platform team's action item; if a specific surface overspends because a product team bypassed the shared infrastructure with a direct model call, that's the product team's.

## Core Concept 8 — Sustained Delivery, Not a Static Policy

Getting the first few surfaces onto a well-measured reasoning-mode policy once is not the end state. New surfaces get proposed, new model versions ship, and the comparison in Core Concept 2 needs to keep running indefinitely:

- **New surfaces onboard through the same approval process by default**, not as an afterthought applied only after a team has already shipped an unreviewed reasoning-mode integration.
- **The review cadence from Core Concept 6 runs on its schedule even when nothing seems to have changed** — the absence of an obvious trigger is not evidence the comparison would still return the same verdict.
- **A program-level retrospective on the cadence** asks explicitly: is the positive-verdict fraction stable or declining, and if declining, is it because standard models are genuinely closing the gap (a real win, not a program failure) or because nobody re-ran the comparison and drift went undetected?

---

## Real-World Examples

- **A pilot's clean quality-per-dollar case funds expansion.** A scheduling-assistant surface, chosen for its unambiguous compounding-error profile, runs the Core Concept 2 comparison on real traffic and shows a clear positive verdict; that concrete before-and-after number, not a general argument about reasoning models being "better," is what the governance group uses to approve expanding the shared infrastructure to a second surface.
- **A quarterly review revokes a surface's default.** A surface approved for reasoning-mode-by-default a year earlier is re-reviewed on its scheduled cadence; the standard model available today closes most of the original quality gap for that surface's actual task mix, and the comparison's verdict flips negative. The surface reverts to standard-model routing, and the freed budget is reallocated — logged as the policy working as designed, not as a mistake in the original approval.
- **An event-triggered review catches drift the schedule would have missed for months.** A vendor ships a new standard-model version mid-quarter with a meaningfully closed gap on multi-step tasks; the event trigger from Core Concept 6 fires a re-review for every surface using that vendor's reasoning model well before the next scheduled quarterly review would have caught it.

## Common Mistakes

- **Letting every product team independently decide whether to call a reasoning model, with no shared measurement.** Produces incomparable, unaudited decisions across the org and no way to know which surfaces are actually justified.
- **Treating adoption count as the success metric.** High reasoning-mode adoption with a declining positive-verdict fraction means the program is delivering less value over time while looking more successful on a naive dashboard.
- **Approving a surface once and never re-reviewing it.** The comparison that justified the original approval decays as standard models improve; without a cadence, the org keeps paying a premium it can no longer justify.
- **Applying one governance bar to every surface regardless of its regulatory or trust sensitivity.** A customer-facing, regulated surface and an internal tooling surface do not carry the same compliance weight and shouldn't clear the same approval process.
- **Building shared routing/cap infrastructure speculatively, before any real pilot exists.** Produces infrastructure shaped by guesses rather than by what a real surface's actual traffic and failure modes required.

---

## Apply it

1. Pick (or hypothesize) two product surfaces that could plausibly use a reasoning model, and for each, sketch the quality-per-dollar comparison from Core Concept 2: what sample would you use, what would "task success" mean for that surface, and what would count as a positive verdict.
2. Design the ownership split from Core Concept 1 for your organization specifically — name who would own the shared infrastructure, who would own the per-surface UX decision, and who would own the comparison methodology.
3. Write the outcome-measure dashboard from Core Concept 5 with real metric definitions for your two surfaces, including at least one exit condition that would trigger revocation.
4. Define both a scheduled and an event-triggered re-review condition from Core Concept 6 for your two surfaces, naming the specific events (which vendor model releases, specifically) that should fire an out-of-cycle review.
5. Draft the one-paragraph support contract the platform team would publish for the shared routing/cap infrastructure, stating what a breaking change requires and who owns an incident in the shared layer versus a surface-specific integration.

## Verify your work

- Each surface's quality-per-dollar comparison is specific and falsifiable — a real sample, a real success-rate definition, a real cost number — not a general statement that "reasoning mode seems worth it here."
- The ownership split names actual roles or teams, not an unowned "someone should handle this."
- The dashboard's exit conditions include an explicit revocation path, not only an expansion path.
- The review cadence names both a schedule and at least one concrete event trigger tied to a specific vendor's model releases.
- The support contract states what happens on a breaking change to the shared infrastructure, not an open-ended "we'll coordinate."

## Review questions

- Why does adoption count fail as the primary success metric for a reasoning-mode governance program?
- What makes the quality-per-dollar comparison something that has to be re-run on a cadence, rather than a one-time approval?
- Why do a scheduled review and an event-triggered review catch different kinds of drift, and why is one insufficient without the other?
- Why should surface revocation be treated as a normal, expected outcome of the policy rather than an exception requiring special justification?
- Why do a customer-facing regulated surface and an internal tooling surface warrant different governance bars for defaulting to reasoning mode?
