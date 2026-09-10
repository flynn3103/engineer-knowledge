# Workflow Fundamentals — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How do you run workflow-pattern choice and autonomy level as an org-wide operating model — shared scaffolding, a real rubric for how much autonomy a new workflow starts with, and clear ownership for the tradeoffs — so every team ships workflows with the same baseline discipline without a central team reviewing every one?

---

## Ownership aligned to who bears the consequences

- The team that owns a workflow's business outcome should own its pattern choice and autonomy level — not a central platform team second-guessing every decision.
- A central team's job is the paved road: shared primitives (chain runner, router, orchestrator harness) and the review rubric — not approving each workflow individually.

## Shared scaffolding as a paved road

- Every team should build chains, routers, and orchestrators on the same shared primitives — not reimplement step execution, retries, and logging per team.
- The paved road should make the least-autonomy default the easy path: a shared chain-runner should be less work to reach for than hand-rolling an agent loop.
- Scaffolding earns trust by being boring and consistent, not by being flexible enough to do anything — flexibility is what teams add on top, deliberately, when the scaffolding's default doesn't fit.

## A rubric for autonomy level, not a vibe

| Question | Answer pushes toward... |
|---|---|
| Can every step be enumerated in advance? | Chain or routing (low autonomy) |
| Does the set of sub-tasks vary per input in a way you can't predict? | Orchestrator-workers (medium autonomy) |
| Does the model need to decide its own next action based on a result it hasn't seen yet? | Full agent loop (high autonomy) |
| What's the cost of the workflow doing something unexpected? | Low cost → more autonomy tolerable; high cost → less |

- Every new workflow answers these questions in writing before autonomy level is chosen — not after, as a retroactive justification.
- A workflow that starts autonomous "because the task might need it later" should instead start at the lowest autonomy level that's provably sufficient today, and only widen with evidence (see Reliability and Recovery, professional level, for the evidence-based widening pattern).

## Cost and reliability accountability

- The team owning a workflow owns its cost per run and its reliability (error rate, retry rate) — these are engineering metrics with an owner, not ambient concerns.
- A workflow that silently escalates in cost (more steps, wider autonomy, more retries) without a corresponding change in its stated business value is a signal for review, not a surprise at the end of the month.

## Rollout decomposition

- New autonomy for a workflow rolls out the same way new code does: staged, with a rollback path.
- Stage 1: run the new pattern/autonomy level in shadow mode alongside the old one, compare outcomes, don't act on the new path's output yet.
- Stage 2: route a small percentage of real traffic to the new path, with the ability to roll back instantly.
- Stage 3: full rollout, with the old path kept available as a fallback for a defined period, not deleted immediately.

## Outcome measures and exit conditions

- Define, before rollout, the specific metric that would justify keeping the new autonomy level (e.g., resolution rate up, human escalation rate flat or down) and the metric that would trigger rollback (error rate up, cost per resolved ticket up beyond a stated threshold).
- Set a review date, not an open-ended "we'll keep an eye on it" — autonomy decisions decay in relevance as traffic patterns shift, and need periodic re-justification the same way a security exception does.

## Cross-Team Contracts and Sustained Delivery

- When one team's workflow calls into a step or sub-agent another team owns, the contract (input/output schema, latency expectation, error behavior) is documented and versioned like an API — because it is one.
- Breaking changes to a shared step follow the same deprecation window as a breaking API change: announce, dual-run, migrate, retire.

## Common Mistakes

- **A central team approving every individual workflow.** This doesn't scale past a handful of teams and turns the platform team into a bottleneck instead of an enabler — the rubric and scaffolding should let teams self-serve within guardrails.
- **Choosing autonomy level once and never revisiting it.** Traffic patterns and failure modes change; a review date forces a periodic re-check instead of permanent drift.
- **Treating cost and reliability as someone else's problem.** If the team shipping the workflow doesn't own its cost per run, nobody has the incentive to notice when it creeps up.

## Real-World Examples

- **A shared chain-runner cuts time-to-ship for simple workflows from weeks to days.** Once the paved road exists, teams building a straightforward routing-plus-chain workflow reach for the shared primitive instead of building bespoke step execution and logging, and ship faster with fewer production incidents from missing retry/timeout handling.
- **A staged autonomy rollout catches a regression before it reaches all customers.** A team widening a workflow from routing to orchestrator-workers runs the new path in shadow mode first; the shadow comparison shows a higher error rate on a specific ticket category, and the team fixes it before any real traffic is affected.

## Apply It

1. Write the rubric your org (or team) should use to decide a new workflow's starting autonomy level, as a short checklist.
2. Design the staged rollout for a workflow moving from one pattern to a more autonomous one — shadow, partial, full — with explicit percentages and a rollback trigger.
3. Write the exit condition (metric + threshold + review date) that would justify keeping a new autonomy level, and the one that would trigger rollback.
4. Identify one shared primitive your team could contribute to a paved road, instead of building bespoke.

## Verify Your Work

- The rubric answers "how much autonomy" with concrete questions, not a subjective judgment call.
- The rollout plan has explicit stages, percentages, and a rollback trigger — not "we'll monitor it."
- The exit condition names a specific metric, threshold, and date — not an open-ended commitment to "keep watching."
- Ownership of cost and reliability for the workflow is assigned to a specific team, not left ambient.

## Review Questions

- Why should a central platform team own scaffolding and a rubric rather than approving every individual workflow?
- What's the risk of choosing a workflow's autonomy level once and never revisiting it?
- Why does a staged rollout (shadow → partial → full) matter for a change in autonomy level specifically, not just for code changes?
- What makes a cross-team step contract different from an internal implementation detail?
