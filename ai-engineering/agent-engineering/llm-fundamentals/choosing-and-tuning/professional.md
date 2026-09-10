# Choosing and Tuning — Professional

<!-- level-focus -->
At professional level, focus on this question:

> Can you set a multi-model strategy — abstraction, lock-in limits, release evaluation, fine-tune lifecycle — that survives model churn without per-team chaos?

---

## Multi-model strategy, deliberately

- Decide which layers of the "one model everywhere" assumption to keep:
  - **Single-family standardization** (one approved family, maximum operational simplicity) vs. **multi-family by design** (frontier for hard tasks, small for volume, a second family as tested fallback).
  - The concentration risk analysis from [How LLMs Work — Professional](../how-llms-work/professional.md) applies at strategy level: what happens to the org when that vendor has a bad quarter?
- Common durable shape: a frontier family for complex/agentic work, a fast/small class for volume, and at least one tested alternative path for critical flows.

## Abstraction with a cutoff

- Standardize the interface layer from [How LLMs Work — Senior](../how-llms-work/senior.md) org-wide — one capability interface, provider SDKs behind it.
- But name the cutoff: abstraction is worth maintaining for *switching and fallback*, not for erasing every vendor difference. Chasing full provider-neutrality (identical behavior everywhere) is a money pit — models differ, and the differences are often the point.

## Evaluating a new release

- Every notable model release triggers the same routine, org-wide:
  1. Refresh the candidate list from leaderboards (candidates only — see [Middle](middle.md)).
  2. Run the affected teams' golden sets (the upgrade evidence bar from [Evaluation Fundamentals](../../agent-evaluation/evaluation-fundamentals/senior.md)) — quality, cost, and latency deltas together.
  3. Update the approved-families list with dated evidence; nothing enters production on reputation.
- Fine-tuned deployments re-run their own held-out evals on any base-model change — a base update can silently invalidate the tune.

## Fine-tune lifecycle governance

- Every fine-tune in production has: a named owner, its training-data snapshot versioned, its held-out eval set recorded, and a review cadence.
- Retirement criteria written down in advance: when a newer base model with a prompt matches the tune's metrics, the tune is retired — carrying fine-tunes forward out of sunk cost is how model estates rot.
- Data governance: training data contains customer data? Same residency/retention rules apply as anywhere else; fine-tuning pipelines are a compliance surface teams forget.

## Common Mistakes

- **Full provider-neutrality as the abstraction goal.** Spends engineering dollars erasing differences that were reasons to choose models.
- **New releases adopted by individual teams ad hoc.** The org ends up on five model versions with five sets of drift behavior and no shared evidence.
- **Fine-tunes without lifecycle ownership.** Orphaned tunes on stale base models, un-retireable because nobody knows what breaks without them.
- **Lock-in assessed only at contract level.** The real lock-in lives in prompt formats, tool-call syntax, and fine-tunes — audit those for portability.

## Apply It

1. Write the org model strategy: standardization vs. multi-family, with the concentration-risk answer stated.
2. Standardize the capability-interface layer; write the explicit cutoff of what it will not abstract.
3. Stand up the release-evaluation routine: golden-set evidence bar, dated approvals, fine-tune re-evals on base changes.
4. Inventory every production fine-tune: owner, data snapshot, eval set, retirement criteria.

## Verify Your Work

- The model strategy states its concentration-risk position and fallback reality, not just preferences.
- Release evaluations produce dated, golden-set-backed decisions recorded in the approved list.
- Every production fine-tune has an owner, versioned data, and written retirement criteria.
- Prompt/tool-call formats have been audited for portability across at least two families.

## Review Questions

- What is the right scope for provider abstraction, and what makes full neutrality a money pit?
- Why must fine-tunes re-evaluate when the base model changes under them?
- Where does real vendor lock-in live, if not in the contract?
