# Scientific and Hypothesis-Driven Thinking — Senior

**Your question:** How do I run experiments safely in production and avoid fooling myself with the results?

Middle level teaches controlled experiments in staging, where you can isolate variables cleanly. Production doesn't give you that luxury — real users, real revenue, and real risk are attached to every treatment group, and the statistics themselves can mislead you if you don't respect how much noise a small sample carries.

## Run production experiments responsibly

An A/B test or staged rollout is still an experiment — baseline (control) and treatment, one variable, measured outcome — but now with blast-radius controls:

- **Start small.** Route 1% or 5% of traffic to the treatment before wider exposure. A bad hypothesis should cost minutes of impact, not hours.
- **Use a feature flag, not a code branch you can't turn off quickly.** The ability to instantly revert to control is what makes running the experiment in production acceptable.
- **Define guardrail metrics up front**, not just the metric you're trying to improve. If checkout conversion is your primary metric, error rate and p99 latency are guardrails — the treatment can't win by breaking something you weren't watching.
- **Decide the stopping rule before you start**, including what triggers an automatic rollback (a guardrail metric crossing a threshold), so the decision isn't made emotionally mid-rollout.
- **Randomize at the right unit.** If users can be affected by other users' treatment assignment (e.g., a shared resource, a marketplace effect), randomizing per-request instead of per-user can leak treatment behavior into the control group and invalidate the comparison.

## Document the experiment before running it

Extend the design template from middle level with the fields production risk adds: an owner, an explicit rollback trigger, and a named decision-maker for the go/no-go call.

```text
Hypothesis:     Mechanism + predicted number, same as before.
Primary metric: The one number that decides the outcome.
Guardrails:     Metrics that must not regress, and the threshold that triggers rollback.
Exposure:       Starting traffic percentage and the ramp-up schedule.
Randomization:  The unit assignment happens at (user, account, session, request).
Analysis date:  The date or sample size at which results will be read — fixed in advance.
Owner:          Who makes the go/no-go call, and who can pull the rollback lever right now.
```

Writing this down before exposure starts is what turns "we're trying something in prod" into an actual experiment — and it's the document a teammate should be able to read afterward to check whether the analysis matched the plan.

### Example guardrail table for a rollout

| Metric | Role | Threshold | Action if breached |
|---|---|---|---|
| Checkout completion rate | Primary | — (read at analysis date only) | N/A — this is what you're testing |
| Payment error rate | Guardrail | > 0.5% absolute increase | Automatic rollback |
| P99 API latency | Guardrail | > 20% relative increase | Automatic rollback |
| Customer support ticket volume | Guardrail | > 2x baseline for the affected flow | Manual review, page owner |

## Statistical significance, in plain terms

You don't need the full theory to avoid the most common trap: **small samples are noisy, and noise looks like a trend if you're not careful.**

- **Sample size determines how much you can trust a difference.** A 2% conversion lift measured over 200 users could easily be random variation; the same 2% lift measured over 200,000 users is much harder to explain as noise alone.
- **A short time window is a small sample in disguise.** "Conversion is up 8% since we shipped this three days ago" often reflects normal day-to-day variance, not a real effect — check what conversion looked like over three-day windows *before* the change, to see how much it naturally swings.
- **Calculate (or estimate) the sample size you need before starting**, based on the smallest effect size that would actually matter to the business. If you'd only act on a 5% improvement, don't stop the test after enough traffic to detect only a 20% improvement reliably.
- **A "statistically significant" result can still be practically meaningless.** A p95 latency improvement of 1ms might be significant with enough traffic and still not be worth the engineering cost or risk of shipping it.

**A concrete illustration:** a checkout flow with a normal week-to-week conversion swing of about ±1.5 percentage points (visible by comparing the same day-of-week across recent weeks, with nothing changed) should not be treated as "moved" by a 1-point difference between control and treatment after a day or two — that's inside the normal swing. A 4-point difference that holds up across a full pre-committed window, on a large enough sample, is a much stronger claim, because it's well outside the range the metric moves on its own.

## The peeking trap (p-hacking in practice)

The single most common way engineers fool themselves in production experiments: **checking the dashboard daily and stopping as soon as the result looks good.**

- **Why it inflates false positives.** Random noise fluctuates above and below zero constantly. If you check every day and stop the first time the metric looks favorable, you're not measuring "did this help" — you're measuring "did noise happen to look good on some day," which happens far more often than a true effect would.
- **Concretely:** a test with no real effect, checked daily over two weeks, has a much higher chance of showing "significant" results on at least one of those days than a single check at a pre-committed end date — the more looks you take, the more chances noise has to fool you.
- **The fix is deciding the analysis moment in advance.** Either commit to a fixed sample size or duration before looking at results, or use a statistical method explicitly designed for repeated looks (sequential testing) — not an ad hoc "check daily, stop when it looks good."
- **Watching dashboards for safety is not the same as analyzing for a decision.** Monitor guardrail metrics continuously to catch a real regression fast — but don't treat a favorable-looking primary metric on day 2 of a planned 14-day test as a reason to call the experiment early.

## Correlation vs. causation in telemetry

Production telemetry constantly hands you correlations — the discipline is not treating them as proof.

1. **Name the mechanism before trusting the correlation.** "Latency dropped after we shipped the cache change" is only strong evidence if you can state *how* the cache change would produce that drop — otherwise it's a coincidence candidate.
2. **Check for a dose-response relationship.** If the cache is really the cause, does cache hit rate track the latency improvement proportionally, or did latency drop by the same amount regardless of hit rate?
3. **Look for what else changed at the same time.** A deploy, a traffic shift, a downstream dependency's own release — any of these could produce the same telemetry signature.
4. **Prefer removal/reintroduction over timing alone.** The strongest evidence: turning the treatment off makes the effect go away, and turning it back on (in a controlled rollout) brings it back.

This is the same discipline `08-debug-thinking` uses at senior level (see [`../08-debug-thinking/README.md`](../08-debug-thinking/README.md)) — but the direction is reversed. Debug-thinking asks "what broke this system?" and works backward from a failure to a cause. This topic asks "did my intentional change actually cause this improvement?" and works forward from a hypothesis to a validated result. Both require ruling out confounders and demanding a mechanism, not just a correlation in time.

## When a controlled experiment isn't safe or possible

Some questions can't be A/B tested — a database migration, a security fix, or a change with legal or safety implications can't ethically be shown to only half of production. When you can't randomize:

- **Use a staged rollout as a weaker substitute for a control group.** Compare metrics before and after full exposure, on the same population, across a matched time window (same day-of-week, same traffic pattern) rather than an arbitrary "yesterday vs. today."
- **Triangulate across independent evidence instead of one clean comparison.** Logs, traces, a timeline of related changes, and a counterfactual estimate (what the metric would likely have looked like without the change, based on its trend beforehand) together can support a causal claim even without a true control group.
- **Be explicit that this is weaker evidence than a randomized test**, and say so when reporting the result — an observational before/after comparison should carry less confidence than a proper controlled experiment, and treating it otherwise is how teams fool themselves.
- **Still define a guardrail and a rollback plan.** The absence of a control group doesn't mean the absence of safety controls — staged exposure and fast rollback still apply.

## A concrete example

**Hypothesis:** Reducing the checkout page's JavaScript bundle size will increase checkout completion rate by improving load time on slow connections.

**Rollout:** Feature-flagged, 5% of traffic, guardrails set on error rate and payment-failure rate, primary metric is checkout completion rate, planned duration is 14 days based on a sample-size calculation for detecting a 3% relative lift.

**Day 2 temptation:** Completion rate in the treatment group is up 6%. A team member suggests shipping to 100% immediately.

**What stops it:** The pre-committed analysis date is day 14, not day 2. A 6% lift on day 2 traffic (a few thousand users) falls well within the natural day-to-day noise observed in historical data — and checking the same comparison on day 5 shows the gap has already narrowed to 1.5%, illustrating exactly why an early peek would have been misleading.

**Day 14 result:** Completion rate lift stabilizes at 1.8%, guardrails unaffected. The mechanism (smaller bundle → faster load → less abandonment on slow connections) is confirmed by a secondary metric: the lift is concentrated almost entirely in the slowest-connection-speed segment, which is the dose-response check that supports causation rather than coincidence.

## Common mistakes at senior level

| Mistake | Consequence | Fix |
|---|---|---|
| Checking results daily and stopping as soon as they look favorable | False positive rate is much higher than the stated confidence level suggests | Commit to a sample size or duration before looking, or use a method built for repeated peeking |
| Treating "statistically significant" as "worth shipping" | Ship changes with real but trivial effects, accumulating complexity for no benefit | Compare the effect size to a pre-defined minimum that would justify the engineering cost |
| Randomizing at the wrong unit when users can affect each other | Treatment leaks into control, biasing the comparison toward "no difference" | Randomize at the unit that matches how the effect could spread (account, session, market) |
| Trusting a correlation in telemetry without naming a mechanism | Ship a "fix" that didn't actually cause the improvement; real cause resurfaces later | Require a stated causal mechanism and check for a dose-response relationship |
| No guardrail metrics, only the metric being optimized | A treatment "wins" on the target metric while quietly breaking something else | Define guardrails before starting; auto-rollback on guardrail breach |
| Treating an observational before/after comparison as equivalent to a randomized test | Overconfidence in a causal claim that's really just a correlation with a plausible story | Triangulate multiple independent signals and explicitly flag the weaker confidence level |
| No named owner for the go/no-go decision or the rollback lever | During an ambiguous result, no one is clearly responsible for calling it, so the rollout drifts | Name the decision-maker and the person who can pull the rollback trigger before exposure starts |

## Hands-on exercise

Take an experiment you've run, or one you're planning to run, in production.

1. Write the primary metric and at least two guardrail metrics, and what threshold on a guardrail triggers an automatic rollback.
2. Estimate (even roughly) the sample size or duration needed to detect the smallest effect size you'd actually act on.
3. Write down the analysis date you'll commit to before looking at results, and describe what you'd do if a teammate wants to stop early because the numbers look good.
4. Identify the randomization unit, and check whether users assigned to different groups could affect each other.
5. Write the mechanism that would explain a positive result, and the dose-response check that would support it.

## Verify your thinking

- [ ] Did you define guardrail metrics and a rollback trigger before starting, not after seeing early results?
- [ ] Did you commit to a sample size or analysis date before looking at results?
- [ ] Can you explain why a favorable result on day 2 of a 14-day test is weaker evidence than the same result on day 14?
- [ ] Did you randomize at a unit that avoids treatment leaking into control?
- [ ] Can you state the causal mechanism and a dose-response check for your result, not just its timing?

Continue to [`professional.md`](professional.md).
