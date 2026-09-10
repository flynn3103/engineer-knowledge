# Evaluation Fundamentals — Professional

<!-- level-focus -->
At professional level, focus on this question:

> Can you define a quality bar, tiered by risk, that multiple teams can be held to without each team re-deriving its own definition of "good enough"?

---

## Quality bar per risk tier

- Not every agent needs the same bar. Define tiers by consequence of failure: e.g., **Tier 1** (informational, low stakes — FAQ lookup), **Tier 2** (reversible action — draft an email a human sends), **Tier 3** (irreversible or financial — issuing a refund, deleting data).
- Each tier gets a minimum required metric set and threshold: Tier 3 might require safety + outcome + trajectory checks all above 99%, with a human-approval gate regardless of score; Tier 1 might only require outcome correctness above 90%.
- Publish the tiers and their bars as a shared document every team building an agent references, instead of each team inventing its own bar.

## Metric ownership

- Assign an owner per shared metric definition (e.g., "safety violation rate" is defined and computed one way, owned by one team) so different teams' "95% pass rate" claims are actually comparable.
- Without ownership, two teams' safety metrics can silently diverge in definition, making a cross-team comparison meaningless while looking rigorous.

## Shared eval platform vs. per-team tooling

- A shared platform (common trace format, common judge infrastructure, common dataset store) avoids every team rebuilding the same golden-set tooling, judge-calibration process, and dashboard.
- Trade-off: a shared platform can become a bottleneck if it can't adapt to a team's specific metric needs — build it with clear extension points (custom graders plugged into a common harness) rather than a closed system.

## Review cadence

- Set a recurring cadence (e.g., quarterly) to review whether the risk tiers, thresholds, and metric definitions still match reality — an agent's real-world failure modes shift as usage grows, and a bar set at launch can become stale.
- Include a review of any metric that's been gated for months without a single blocked deploy — it may be miscalibrated (threshold too loose) or genuinely no longer needed.

## Avoiding metric theater and Goodhart drift

- **Metric theater**: reporting a metric that looks rigorous but that no decision actually depends on — it exists to appear evaluated, not to inform anything.
- **Goodhart's law**: "when a measure becomes a target, it ceases to be a good measure" — once a team optimizes directly for a metric (e.g., judge pass rate), the metric can be gamed (verbose answers that pattern-match what the judge rewards) without the underlying quality improving.
- Counter with periodic human spot-checks that don't use the automated metric, comparing them to what the metric reports — a growing gap is the signal the metric has drifted.

## Common Mistakes

- **Every team defining its own risk tiers and bars.** Produces incomparable claims of "quality" across the org and duplicated effort building the same infrastructure.
- **A shared platform with no extension point for custom graders.** Teams route around it with shadow tooling, defeating the point of having a shared standard.
- **Never re-reviewing thresholds after launch.** A bar that made sense at 100 users a day can be badly wrong at 100,000.

## Apply It

1. Define at least two risk tiers relevant to your organization's agents, with the minimum metric set and threshold for each.
2. Name an owner for each shared metric definition used across more than one team.
3. Set a review cadence and put it on a calendar, including a spot-check of at least one metric against unaided human judgment.

## Verify Your Work

- Risk tiers are documented with concrete thresholds, not vague severity labels.
- Each shared metric has one named owner and one definition, referenced by every team using it.
- A review cadence exists and includes a human spot-check independent of the automated metric.

## Review Questions

- Why does an unowned shared metric lead to incomparable claims across teams?
- What's the difference between metric theater and a metric that's actually acted on?
- How does Goodhart's law apply to an LLM-as-judge score specifically, and what's a concrete countermeasure?
