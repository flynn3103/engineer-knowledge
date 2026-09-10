# Reliability and Recovery — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How do you define org-wide standards for which risk tier applies to which action, and run a review process that decides — and periodically re-decides — how much autonomy a workflow is allowed, without either a rubber-stamp process or a bottleneck that blocks every team on every action?

---

## A standard risk-tier framework, shared across teams

- Every team's high-stakes steps should be classified using the same tier definitions (from senior level: read-only, low-value write, hard-to-reverse write, destructive/irreversible) — not each team inventing its own scale, which makes cross-team comparison and central risk oversight impossible.
- Publish the framework with concrete examples per tier so a new team can self-classify a new action without a central review for every single case.

## Ownership split

- The team that owns the workflow owns the day-to-day tiering decision and gate implementation for its own actions — a central risk/compliance function owns the framework itself, sets the bar for Tier 3/4 actions, and reviews new high-risk actions before launch, not every gated proposal after launch.
- This mirrors the ownership pattern from Orchestration and Delegation's professional level: central teams provide the paved road and rubric; delivering teams operate within it.

## The review process for a new high-risk action

1. The owning team classifies the new action's tier using the shared framework and documents the reasoning (reversibility, exposure, blast radius).
2. For Tier 3/4 actions, a central review confirms the tiering and gate design (timeout, fallback, evidence bar for widening) before launch — this is a gate on the design, not a rubber stamp on volume.
3. The action launches fully gated (100% human approval) regardless of team confidence, per the evidence-based widening principle from senior level.

## Periodic autonomy review, not a one-time decision

- Every autonomy-widening decision (an auto-approve threshold granted from logged evidence) gets a review date, not a permanent grant — traffic patterns, fraud patterns, and policy changes shift over time, and a threshold set six months ago may no longer be safe.
- The review re-examines the underlying evidence: has the rejection rate for the auto-approved band crept up? Has the volume changed enough that the original sample size no longer represents current traffic?

## Rollout decomposition

- New autonomy for a high-risk action rolls out staged, mirroring a code rollout: shadow (log what the gate would have decided without acting on it), partial (a small percentage of real traffic auto-approved, rest still gated), full (once the partial stage's evidence holds up).
- Keep the ability to tighten back down at every stage — a widening decision is not one-directional.

## Outcome measures and exit conditions

- Before widening, define the specific metric that justifies keeping it (rejection rate stays at zero or near-zero over N further cases) and the metric that triggers reverting to fully gated (any rejection in the auto-approved band, or a shift in the underlying traffic pattern).
- Set the review date up front, as part of the widening decision itself — not as an afterthought.

## Cross-Team Contracts and Sustained Delivery

- When one team's workflow gates an action that another team's downstream process depends on (e.g., a refund gate that a billing reconciliation process expects to resolve within a bounded time), the gate's timeout and fallback behavior is a contract the downstream team can rely on — document it the same way you'd document an API's latency SLA.
- Audit logs for gated actions (who approved, what was proposed, what evidence justified any auto-approval) should be centrally queryable, not siloed per team, so a compliance or incident review doesn't require asking every team individually for their logs.

## Common Mistakes

- **Each team inventing its own risk-tier scale.** Makes it impossible for a central function to reason about risk consistently across the org, and duplicates the work of defining what "high-risk" means.
- **A central team rubber-stamping every widening request without checking the underlying evidence.** Defeats the purpose of the evidence-based widening principle — the review has to actually look at rejection rates and sample size, not just approve because a team asked.
- **No review date on an autonomy-widening decision.** A threshold that made sense for last year's traffic pattern can quietly become unsafe as patterns shift, with nobody checking until an incident forces the question.
- **Siloed audit logs per team.** Slows down any cross-team incident investigation or compliance audit that needs to reconstruct what happened across multiple gated workflows.

## Real-World Examples

- **A shared risk-tier framework speeds up a new team's launch.** A team building a new high-stakes workflow classifies their action using the existing framework and examples, and gets through central review in days instead of weeks, because the reviewer isn't evaluating a novel risk-tier scale invented for this one case.
- **A periodic review catches a drifting auto-approve threshold before an incident.** A quarterly review of an auto-approved refund band finds the rejection rate has crept from 0% to 3% as customer behavior shifted; the threshold is tightened before it causes a measurable loss, rather than after.

## Apply It

1. Write the shared risk-tier framework your org should use, with at least one concrete example action per tier.
2. Define the review process for a new Tier 3/4 action: who classifies it, who confirms the classification, what launches fully gated regardless.
3. Write the review cadence (e.g., quarterly) and the specific evidence question asked at each review for an existing auto-approve threshold.
4. Identify one piece of gate/audit infrastructure (logging, review tooling) that should be centrally shared rather than built per team.

## Verify Your Work

- The risk-tier framework has concrete example actions per tier that a new team can match against without inventing their own scale.
- The review process distinguishes what the owning team decides from what central review confirms.
- Every autonomy-widening decision has a stated review date and a specific evidence question for that review — not an open-ended grant.
- Audit logs for gated actions are queryable centrally, not siloed per team.

## Review Questions

- Why does a shared risk-tier framework matter more than each team defining its own?
- What's the difference between central review confirming a team's tiering decision and rubber-stamping it?
- Why does an autonomy-widening decision need a review date even when the initial evidence looked solid?
- Why should audit logs for gated actions be centrally queryable rather than siloed per team?
