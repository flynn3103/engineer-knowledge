# Decoding and Sampling — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How do you run decoding-parameter standards — default profiles per task category, override governance, regression testing, cost trade-offs — as a durable, org-wide operating model, so a dozen teams stop independently rediscovering (or getting wrong) the same settings?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core Concept 1 — Default Sampling Profiles as a Paved Road

The predictable organizational failure mode this file addresses: without a shared default, every team calling an LLM API independently guesses at temperature, top-p, and penalty settings — usually by copying whatever example was closest at hand, exactly as in the `middle.md` scenario where a chat-tuned temperature leaked into an extraction endpoint. Multiply that across a dozen services and an org ends up with a dozen undocumented, inconsistent, unreviewed decoding configurations, some of them silently wrong for their task.

The fix is the same shape as any other paved-road platform decision: define a small number of **named, versioned decoding profiles**, one per task category, published somewhere every team can find and import rather than reinvent:

```yaml
# decoding-profiles.yaml — owned by the AI platform team, versioned in a shared repo
profiles:
  extraction-v2:
    description: "Structured field extraction from documents"
    temperature: 0
    response_format: json_schema   # constrained decoding, not prompt-only
    top_p: 1
    repetition_penalty: none

  conversational-v3:
    description: "Balanced assistant / chat replies"
    temperature: 0.7
    top_p: 0.9
    repetition_penalty: none

  creative-v1:
    description: "Brainstorming, ideation, long-form creative generation"
    temperature: 1.1
    top_p: 0.95
    presence_penalty: 0.3
```

Services import a named profile (`extraction-v2`) rather than hardcoding raw numbers, the same way a service imports a shared library version rather than vendoring a copy of the logic. A profile change becomes a version bump every consumer can see and adopt deliberately, instead of an invisible per-service drift nobody can audit.

## Core Concept 2 — Governance: Overrides Are an Exception Process, Not Silent Drift

A paved road only stays trustworthy if deviating from it is visible. Publishing default profiles solves nothing if any team can still quietly set `temperature=0.9` on an extraction call and nobody else in the org can see that happened. The governance layer:

- A team that needs to deviate from a standard profile files a lightweight, documented exception — what profile they're deviating from, what specific value they're changing, and why (a genuinely unusual task shape, a measured accuracy improvement, a latency constraint) — reviewed by whoever owns the shared profile library (an AI platform or ML infra team, in most orgs).
- The exception is recorded somewhere queryable — a config flag, a tagged override in the same shared repo — not left as tribal knowledge in one engineer's head or a Slack thread.
- A monitoring expectation comes with the exception: the deviating service still reports its malformed-output rate (or equivalent task-specific quality signal) so a bad override shows up in the same dashboards as everything else, rather than becoming an unmonitored outlier.

The point isn't to block every deviation — some tasks genuinely need a nonstandard setting. The point is that deviation should be a *decision with a record*, not an accident nobody can find later when debugging a quality regression.

## Core Concept 3 — Regression Testing for Decoding-Parameter Changes

A default profile is not a fire-and-forget config value — changing `extraction-v2`'s temperature from `0` to `0.1`, or its top-p from `1` to `0.95`, is a change with the same blast radius as a prompt change, because it changes the output distribution for every service that imports that profile. Treat it accordingly, aligned with the discipline covered in [Prompt Engineering](../prompt-engineering/README.md) for versioning and testing prompt changes:

1. **Version the profile** (`extraction-v2` → `extraction-v3`), never mutate a profile in place under the same name — a consuming service pinned to `extraction-v2` should keep getting exactly that behavior until it deliberately upgrades.
2. **Test the new version against a held-out evaluation set** before it's offered as the new default — schema-validity rate for an extraction profile, a rubric or preference-based score for a conversational profile — and compare against the current version's baseline on the same set.
3. **Roll out gradually** — canary the new profile version on a small percentage of one consuming service's traffic, confirm the quality signal holds or improves, before making it the org-wide default for new adopters.
4. **Keep the old version available** for some deprecation window so a service that upgrades and regresses can roll back to a known-good pinned version immediately, rather than waiting on a fix to the new one.

## Core Concept 4 — Cost: Self-Consistency Multiplies Spend for a Reliability Gain

**Self-consistency** (majority-vote sampling) is a real technique for improving reliability: sample the same prompt `N` times at a nonzero temperature, and take the most common answer among the `N` samples rather than trusting a single sample. It works because independent sampling errors are less likely to agree with each other than the correct answer is likely to recur across samples — but it costs roughly `N` times the inference spend of a single call, for exactly the reliability gain the extra `N-1` calls bought.

```
Single call:        $0.002 / request
Self-consistency N=5: ~$0.010 / request   (5x)
Self-consistency N=10: ~$0.020 / request  (10x)
```

That multiplier is only justified with an explicit cost-per-reliability-point argument, not applied by default because it's available:

```
Baseline malformed-output rate (single sample):     6%
Malformed-output rate with N=5 self-consistency:     1%
Cost multiplier: 5x
Is a 5-point reliability gain worth 5x the per-request cost,
for this specific workflow's actual cost of a malformed output?
```

For a workflow where a malformed output triggers a cheap automatic retry, 5x the cost for a 5-point improvement is very likely not worth it — the retry is nearly free by comparison. For a workflow where a malformed output silently corrupts a downstream financial record that's expensive to detect and fix later, the same 5-point improvement can easily justify 5x the cost. The number that matters is not "does self-consistency help" (it usually does, some amount) — it's whether the *specific, quantified* reliability gain is worth the *specific, quantified* cost multiplier for that workflow's actual failure cost. Default-on self-consistency across every service is a cost decision made without that comparison ever happening.

## Core Concept 5 — Cross-Team Scenario: Standardizing a Dozen Services' Decoding Defaults

An org discovers, via an internal audit, that a dozen LLM-calling services have wildly inconsistent and largely undocumented decoding settings — several structured-extraction services are running at `temperature=1.0` because that was the SDK's default and nobody had explicitly overridden it, and those services show the highest malformed-output rates in the fleet.

**Rollout, decomposed into reversible increments:**

1. **Audit.** Centrally query or log the actual decoding parameters each of the twelve services sends in production — not what a config file claims, what's actually on the wire — and cross-reference against each service's current malformed-output or quality-incident rate. This produces a ranked list, not a vague impression of "some services are probably misconfigured."
2. **Identify the worst offender.** The service with both an off-profile temperature and the highest malformed-output rate is the pilot — the same principle as piloting a golden base image on the service most obviously helped by it, so the win is concrete and measurable rather than hypothetical.
3. **Pilot the standardized profile on that one service.** Apply `extraction-v2` (temperature 0, structured output on), measure the before/after malformed-output rate and cost per request on that service specifically.
4. **Expand service by service**, prioritized by current malformed-output rate and business criticality, each verified against its own before/after numbers rather than assumed to inherit the pilot's result automatically — a service with an unusual input distribution may need its own eval pass before adopting the default.
5. **Wire the governance and regression-testing practices from Core Concepts 2 and 3 into the rollout itself**, so profile adoption isn't a one-time cleanup that drifts again in a year — new services onboard onto a named profile by default, not by copying whatever the nearest example happened to use.

**Outcome measures, tracked centrally and reviewed on a regular cadence:**

```yaml
metrics:
  malformed_output_rate: "invalid outputs / total outputs, per service and fleet-wide"
  cost_per_request: "tracked per profile, to catch an accidental self-consistency or
                      high-temperature setting inflating spend without a matching quality gain"
  eval_pass_rate_trend: "task-specific eval score for each profile version, tracked
                          release over release, to catch a profile regression early"
exit_conditions:
  pilot_to_expansion: "pilot service's malformed-output rate drops measurably, with
                        a before/after number, and cost per request does not increase
                        unexpectedly"
  program_maturity: "all twelve services on a named, versioned profile (not raw
                      hardcoded parameters), and fleet-wide malformed-output rate
                      trending down for two consecutive review cycles"
```

`malformed_output_rate` is the outcome measure that actually proves the standardization delivered value — the earlier `middle.md` lesson about measuring a schema-validity rate rather than eyeballing a few outputs applies at fleet scale the same way it applies to a single service. Adoption of the standardized profiles (a fraction of services using a named profile versus a raw hardcoded config) is a useful leading indicator, but a fleet that's 100% "adopted" while malformed-output rate hasn't moved means the profiles chosen weren't actually the right ones, or the worst offenders weren't prioritized first.

## Real-World Examples

- **An accidental default costs an org real money and quality before anyone notices.** Several structured-extraction services inherit `temperature=1.0` because that was the SDK client's own default and nobody explicitly set it — the audit in Core Concept 5 is what surfaces this, not a single team's investigation, because no individual team had a reason to suspect their config was unusual until compared against the fleet.
- **A pilot's concrete before/after number funds the rest of the rollout.** The worst-offending extraction service's malformed-output rate drops from double digits to near zero after adopting the standardized profile, with matching before/after numbers — that concrete result, not a mandate, is what gets the next eleven teams to prioritize adopting the profile on their own roadmap.
- **Self-consistency gets turned on by default and quietly triples a service's monthly inference bill.** A team enables `N=3` self-consistency on a workflow after reading that it improves reliability, without measuring the actual malformed-output rate before and after — the bill increase is immediate and easy to see; the reliability gain, never measured, turns out to be marginal for that specific workflow once someone finally checks.

## Common Mistakes

- **Publishing default profiles with no governance for overrides.** Without a documented exception process, deviation from the standard is just as invisible as it was before the profiles existed — the paved road exists but nobody can tell who's actually using it.
- **Mutating a shared profile in place instead of versioning it.** A silent change to `extraction-v2`'s definition changes behavior for every consuming service simultaneously, with no ability to roll back a single service independently.
- **Treating decoding-parameter changes as configuration, not as a regression-testable change.** A temperature or top-p change to a shared profile can shift output quality as much as a prompt change would, and deserves the same eval-set-before-rollout discipline.
- **Turning on self-consistency (or any N-sample strategy) without a quantified cost-per-reliability-point justification.** Multiplying spend by `N` for an unmeasured reliability gain is a cost decision made without evidence.
- **Measuring only adoption of standardized profiles, never the fleet-wide malformed-output rate.** High adoption with no movement in the outcome metric means the standardization effort picked the wrong priorities or the wrong profile values, not that the program succeeded.
- **Standardizing before auditing.** Designing the "right" default profiles by committee, without first auditing what the fleet is actually running and which services are hurting most, produces profiles tuned to guesses rather than to the real worst offenders.

---

## Apply it

1. Inventory the actual decoding parameters (not the assumed ones) sent by every LLM-calling service you have visibility into, and cross-reference against any quality or malformed-output signal you already track.
2. Design two or three named, versioned decoding profiles covering the task categories represented in that inventory (at minimum an extraction-style and a conversational-style profile).
3. Identify the single worst-performing service from the inventory and pilot one profile on it, recording a concrete before/after malformed-output rate and cost-per-request number.
4. Write the governance rule for overrides: who reviews an exception request, what has to be documented, and what monitoring commitment comes with an approved deviation.
5. For one workflow in your inventory, work through the self-consistency cost-per-reliability-point calculation from Core Concept 4 using real or reasonably estimated numbers, and state whether it would be justified for that specific workflow.

## Verify your work

- Your inventory names specific services and their actual decoding parameters, not a general impression that "some services are probably misconfigured."
- Your pilot has a real before/after number for both malformed-output rate and cost per request, not just a qualitative "it seems better."
- Your governance rule specifies who approves an override and what monitoring commitment is attached — not just "teams can deviate if they have a good reason."
- Your profiles are versioned in a way that lets a consuming service roll back to a prior version independently of other consumers.
- Your self-consistency cost calculation states an explicit reliability gain, an explicit cost multiplier, and a conclusion about whether that trade was worth it for that specific workflow — not a general endorsement or rejection of the technique.

## Review questions

- Why does publishing standardized decoding profiles fail to prevent silent drift unless it's paired with an override governance process?
- Why should a change to a shared decoding profile's default temperature go through the same regression-testing discipline as a prompt change?
- What specifically does self-consistency (majority-vote sampling) trade, and what number would you need before deciding whether that trade is worth it for a given workflow?
- In the twelve-service rollout scenario, why does the audit step come before designing the standardized profiles rather than after?
- Why can a fleet reach high adoption of standardized profiles while its outcome metric (malformed-output rate) fails to improve, and what does that gap indicate?
