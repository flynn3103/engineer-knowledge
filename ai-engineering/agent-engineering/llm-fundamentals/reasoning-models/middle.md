# Reasoning Models — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Can you classify your tasks into reasoning-helps and reasoning-wastes, control the effort dial, and explain why high temperature sabotages reasoning?

---

## Classify every task before choosing the model class

| Task shape | Reasoning model? | Why |
|---|---|---|
| Extraction, formatting, templating | **No** | Nothing to figure out; deliberation is pure overhead. |
| Classification, routing | **No** | Pattern-matching, not multi-step logic; standard model at temp 0 is equal and cheaper/faster. |
| Lookup, summarization | **No** | The difficulty is information access (retrieval), not inference. |
| Multi-step math, constraint problems | **Yes** | Step-checking catches the early plausible-but-wrong answer. |
| Planning and decomposition | **Yes** | Ordered sub-tasks before acting is exactly what thinking tokens produce. |
| Hard debugging, root-cause style analysis | **Yes** | Form-and-discard hypotheses needs deliberation. |
| Tool-use workflows | **Usually no** | The loop's iterative tool calls *are* the deliberation; a reasoning model adds a redundant inner one (see [Senior](senior.md)). |

## The effort dial

- Most reasoning models expose **reasoning effort** (low/medium/high, or a token budget): how much thinking to allow before answering.
- Higher effort → better on genuinely hard tasks → more tokens, more latency, on *every* request. It's a cost dial as much as a quality dial.
- Match effort to task difficulty: low for moderate tasks, high only for the hard tail. A fixed "high everywhere" setting is the most common way to 10× a bill for marginal quality.

## The temperature interaction — why they fight

- Reasoning depends on **coherent multi-step chains**: each thinking step builds on the last, and a single off-track token can send the whole chain wandering.
- **High temperature deliberately increases the chance of off-track tokens.** Stacking temperature 1.0 onto a reasoning task is paying for deliberation and then injecting noise into it — the chain derails more often, and you pay for the derailed attempts.
- Rule: reasoning tasks want **low temperature** (often the model ignores the setting anyway — many reasoning classes use fixed internal sampling). Don't "make it creative" on a math or planning path.

## The cost/latency multiplier, concretely

- Typical pattern for a moderately hard task: standard model ≈ 600 output tokens, ~2s. Reasoning model at medium effort ≈ 2,500 thinking + 600 visible tokens, ~15s.
- That's ~4–5× the output cost and ~7× the latency — fine for a nightly batch analysis; unacceptable inside a chat reply.
- Measure your own multiplier from usage fields; it varies by task and effort setting.

## Common Mistakes

- **"High effort everywhere."** Pays peak prices on easy requests that never needed thinking.
- **High temperature on reasoning paths.** Directly sabotages the chain-of-thought coherence you're paying for.
- **Choosing a reasoning model to fix retrieval failures.** The model reasons beautifully over the wrong or missing facts you gave it.
- **Ignoring latency until users complain.** Hidden thinking time lands entirely on the interactive path; measure it per task before shipping.

## Apply It

1. Put every LLM task in your app through the table above; mark each reasoning / standard, with one-line justification.
2. For any reasoning usage, set the effort dial per task difficulty — and find the multiplier (tokens, seconds) on a real task, not from docs.
3. Audit sampling settings on every reasoning path: confirm low temperature, and note if the model overrides it anyway.

## Verify Your Work

- Every reasoning-model choice maps to a "Yes" row in the task table, not to importance or novelty.
- Effort settings vary with task difficulty, and the cost multiplier is measured from usage data.
- No reasoning path runs at creative temperature.

## Review Questions

- Why is a tool-use agent loop usually the wrong place for a reasoning model?
- What does the effort dial actually control, and why is "high everywhere" a bill multiplier?
- Why does high temperature specifically sabotage reasoning quality?
