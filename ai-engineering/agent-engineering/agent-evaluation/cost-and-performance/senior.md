# Cost and Performance — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Can you make cost and latency design constraints from the start — with caps, budgets, and routing decisions validated by evals — rather than a bill you react to after the fact?

---

## Per-run caps and breach behavior

- Set explicit per-run caps: maximum tokens, maximum steps, maximum cost. Define what happens on breach — does the run stop and escalate to a human, does it return a partial answer, does it hard-fail — rather than leaving an uncapped run free to consume unbounded cost on a pathological input (e.g., a non-terminating loop, see [Reliability and Recovery](../../agent-workflow/reliability-and-recovery/)).

## Latency budget allocated across steps

- Set a total latency budget for the run (e.g., "under 5 seconds for a real-time chat response"), then allocate it across steps — a 3-step run might budget 1s for routing, 3s for the main reasoning step, 1s for formatting — so a single step can't silently consume the whole budget without anyone noticing until the run is already too slow.
- Track **p95/p99 latency**, not just average — the average can look fine while a meaningful fraction of users experience a much slower tail, especially once a fan-out join (see [Scaling Workflows — Senior](../../agent-workflow/scaling-workflows/senior.md)) is in the mix.

## Model routing and cascades

- **Cascade**: try a cheap/fast model first; only escalate to a more expensive model if the cheap model's response is low-confidence or fails a validation check. Reduces average cost while preserving quality on the harder cases that actually need the stronger model.
- **Routing**: classify the request up front and send it to whichever model tier fits its complexity, rather than sending every request to the most expensive model by default.
- Either approach needs validation against the eval suite (see [Datasets and Graders](../../datasets-and-graders/)) — confirm the cascade's escalation trigger actually catches the cases that need the stronger model, not just cases that happen to look uncertain by some proxy signal that doesn't correlate with actual difficulty.

## Cost regressions caught in CI

- Track token/cost-per-run as a metric in your eval pipeline, the same way you'd track a correctness metric — a prompt change that adds an unnecessary paragraph to the system prompt, multiplied across every call, is a regression worth catching before it ships, not after a monthly bill spike.

## Rate-limit interaction

- Cost control and rate limits interact: a retry-on-failure policy that doesn't back off can itself trigger a provider's rate limit, causing more failures and more retries — a runaway feedback loop that increases both cost and error rate simultaneously. Ensure retry logic backs off and respects rate-limit signals rather than retrying blindly (see [Reliability and Recovery — Junior](../../agent-workflow/reliability-and-recovery/junior.md)).

## Common Mistakes

- **No per-run cap, relying on "it shouldn't loop forever" as the only safeguard.** A single pathological input can consume unbounded cost with no automatic stop.
- **Tracking average latency only.** Masks a slow tail that a meaningful fraction of users actually experience.
- **Deploying a cascade or router without validating the escalation trigger against the eval suite.** Risks routing genuinely hard cases to the cheap model, trading invisible quality loss for a visible cost saving.
- **No cost regression tracking in CI.** A prompt change that quietly inflates token usage ships without anyone noticing until the bill reflects it weeks later.

## Apply It

1. Set an explicit per-run cap (tokens, steps, cost) for your highest-risk agent, with a defined breach behavior.
2. Add p95/p99 latency tracking alongside average latency for at least one agent.
3. If using a cascade or router, validate its escalation/routing trigger against the eval suite and report the pass-rate impact.
4. Add token/cost-per-run as a tracked metric in your CI or release pipeline.

## Verify Your Work

- Every high-risk agent has an explicit per-run cap with a defined, tested breach behavior.
- Latency is tracked at p95/p99, not only average.
- Any cascade/routing trigger has been validated against the eval suite, with the pass-rate impact recorded.
- Cost-per-run is tracked as a CI metric, not discovered only from a monthly bill.

## Review Questions

- Why does an uncapped run risk unbounded cost, and what's the fix?
- Why does p95/p99 latency matter more than average for a user-facing agent?
- Why must a cost-saving cascade or router be validated against the eval suite before shipping?
