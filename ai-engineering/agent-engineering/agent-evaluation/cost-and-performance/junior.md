# Cost and Performance — Junior

<!-- level-focus -->
At junior level, focus on this question:

> Can you compute what a single run cost and where its latency went, using only the recorded trace?

---

## Cost sources

- **Input tokens**: everything sent to the model — system prompt, conversation history, tool results fed back in. Usually priced lower per token than output.
- **Output tokens**: everything the model generates — the response, plus any reasoning/thinking tokens some models produce, which are billed even though the user never sees them directly.
- **Cached-input tokens**: if the provider supports prompt caching and a prefix repeats across calls, cached tokens are usually billed at a steep discount versus fresh input tokens.
- Each token type can have a different price per token — a run's total cost is the sum across all three, not just output tokens (a common mistake, since output is the only part a person directly reads).

## Computing per-run cost from a trace

1. Pull input, output, and cached-input token counts from every span in the trace (see [Tracing and Observability — Junior](../../tracing-and-observability/junior.md)).
2. Multiply each by its per-token price for the specific model used.
3. Sum across every span in the run — a 3-step agent run has 3 separate model-call costs to add together, not just the final step's cost.

## Step count

- More steps generally means more cost (each step is at least one more model call) and more latency. A run that took 8 steps to resolve a request that should take 2 is worth investigating even if the final answer was correct — see [Debugging Agent Failures](../../debugging-agent-failures/) for the non-terminating-loop failure mode.

## Latency: TTFT vs. total

- **TTFT (time to first token)**: how long before the model starts responding — matters for perceived responsiveness in an interactive context.
- **Total latency**: how long the entire run took, across every step, until a final answer is produced.
- **Per-step breakdown**: total latency split by step, so you can see whether one specific tool call or model call is the slow part, rather than only knowing the run "felt slow."

## Common Mistakes

- **Counting only output tokens as the cost.** Ignores input tokens, which are often the larger share of cost in an agent with a long system prompt or conversation history.
- **Reporting only total latency with no per-step breakdown.** Can't tell you whether the slow part is the model thinking or a tool call waiting on an external API.
- **Not noticing an unusually high step count.** A correct answer reached via 8 steps instead of 2 is still a cost and latency problem worth investigating.

## Apply It

1. Pick one multi-step run's trace. Compute the cost of each span (input + output + cached tokens × price), then sum for the full-run cost.
2. Break down the total latency by step and identify the slowest single step.
3. Note the step count and whether it looks reasonable for the complexity of the request.

## Verify Your Work

- The computed cost includes input, output, and cached tokens for every span, not just the final output.
- Latency is reported per step, not only as one total number.
- Step count is checked against what a reasonable resolution should take.

## Review Questions

- Why does counting only output tokens understate a run's real cost?
- What can a per-step latency breakdown tell you that a single total latency number can't?
- Why is an unusually high step count worth investigating even when the final answer is correct?
