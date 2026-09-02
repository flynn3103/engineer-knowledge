# Choosing the Right Model — Junior

<!-- level-focus -->
At junior level, focus on this question:

> Given one well-specified task — for example, summarizing support tickets — can you pick a suitable model using a simple checklist (task type, quality bar, latency need, budget) and explain the choice in one paragraph?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core Concept 1 — Vocabulary: Tiers, Latency, Context, Modality

Five properties describe almost any model you'll choose between:

- **Capability tier** — models cluster into roughly two bands. **Frontier-class** models (GPT-4o/o1/o3-class, Claude Opus-class, the largest Gemini variants) are the most capable at open-ended reasoning, ambiguous instructions, and hard multi-step tasks. **Small/fast-class** models (GPT-4o-mini-class, Claude Haiku-class, smaller open-weight models like a 7-8B Llama or Mistral variant) are meaningfully less capable on hard reasoning but perform close to frontier-level on narrow, well-specified tasks like extraction, classification, and short summarization.
- **Cost per token** — providers price per input/output token, and the tiers above map directly to price: a frontier-class model typically costs several times more per token than that same provider's mini/small-class model. This is not a minor difference — at meaningful volume it is often the single largest line item in the decision.
- **Latency** — how long a request takes, usually described as time-to-first-token (for streaming, interactive use) and total completion time (for batch use). Small/fast-class models are, as the name implies, faster per token and often have lower time-to-first-token than frontier models, independent of the task.
- **Context length** — the maximum number of tokens (input plus output combined, for most providers) a model can process in one request. If your input — a document, a chat history, a codebase excerpt — doesn't fit, it must be truncated or chunked before you ever get to compare quality.
- **Modality and tool-calling support** — not every model accepts images or audio as input (multimodal vs. text-only), and not every model supports structured tool/function calling, or supports it equally reliably. Both are binary eligibility checks, not quality trade-offs: a model that can't accept an image attachment is simply not a candidate for a task that requires reading one.

## Core Concept 2 — The Four-Question Checklist

Before comparing specific models, answer four questions about the task itself:

1. **What does "good enough" look like, concretely?** Not "high quality" — write down what a correct output contains and what an incorrect one looks like. A ticket summary that captures the customer's issue and the resolution is good enough even if it isn't eloquent; a summary that omits the resolution is wrong regardless of how well-written it is.
2. **How fast does a response need to be?** A user waiting in a chat UI needs a response in low single-digit seconds. A nightly batch job summarizing yesterday's tickets can tolerate many seconds or even minutes per item, because nothing downstream is waiting on any single request.
3. **What does this cost at your actual volume?** A cost per request that looks trivial in a demo (fractions of a cent) becomes a real budget line the moment you multiply by daily volume. Do this multiplication before picking a model, not after the first invoice.
4. **Does the input fit the context window, and does the task need a modality or tool-calling support beyond plain text?** Check this before anything else — it can eliminate models from consideration outright, the same way a hard constraint does at senior level.

## Core Concept 3 — Worked Example: Support-Ticket Summarization

A team is building a feature that reads a support ticket thread and produces a 2-3 sentence summary for the agent dashboard. Walking the checklist:

| Question | Answer for this task |
|---|---|
| Quality bar | Summary must name the customer's issue and, if resolved, the resolution. Extractive, not creative — no need for nuanced reasoning or multi-step problem-solving. |
| Latency need | Generated when a ticket is closed, shown on a dashboard later — not blocking any user-facing action. A few seconds per ticket is fine. |
| Volume / budget | 50,000 tickets/day. Even a small per-token cost difference multiplies into a meaningful daily total at this volume. |
| Context length | Ticket threads run 500-2,000 tokens; well within any current model's context window — not a limiting factor here. |
| Modality / tool-calling | Text only, no attachments to read, no tool calls needed. |

The task is narrow, extractive, and not latency-sensitive. A frontier-class model would almost certainly produce a good summary — but so would a mini/haiku-class model, at a fraction of the per-token cost, because summarizing a well-structured, moderate-length text thread doesn't require the deep multi-step reasoning that separates frontier models from smaller ones. The right choice here is to start with a small/fast-class model and confirm it clears the quality bar (Core Concept 4), reserving the frontier-class model's cost for tasks that actually need its extra capability.

## Core Concept 4 — Confirming the Choice: A Small, Manual Spot-Check

At junior level, "confirm it clears the bar" means a manual spot-check, not a formal bake-off (that's the middle-level skill):

1. Pull 5-10 real examples of the task's input (real ticket threads, not invented ones).
2. Run each through your candidate model with the prompt you intend to use in production.
3. Read every output against the quality bar you wrote down in Core Concept 3, row by row — does it name the issue? Does it name the resolution when one exists?
4. If every output passes, the small/fast-class model is a reasonable starting choice. If several fail in the same way (for example, consistently dropping the resolution), that's a signal either the prompt needs work or the task needs more capability than this tier provides.

## Common Mistakes

1. **Defaulting to the most capable (and most expensive) model "just in case."** For a narrow, well-specified task, this pays frontier-level cost and latency for no quality benefit the task actually needed.
2. **Ignoring context window size until a long input silently gets truncated.** A ticket thread that grows past the context limit doesn't necessarily error — some clients truncate silently, and the summary is then based on incomplete input with no obvious warning sign.
3. **Picking "the model everyone talks about" instead of the model that fits this task.** A model's general reputation is not evidence about your specific, narrower task.
4. **Not multiplying per-request cost by real volume before deciding.** A cost that looks negligible per request is a very different number at 50,000 requests/day versus 50 requests/day.
5. **Not checking modality or tool-calling support before evaluating quality.** Discovering a model can't accept the image attachment your task requires, after you've already judged its text quality favorably, wastes the evaluation.

## Apply it

1. Pick a real, well-specified task you have (or invent a realistic one: classifying incoming emails into three categories, extracting a shipping address from free text, drafting a one-line changelog entry from a commit message).
2. Fill out the four-question checklist from Core Concept 2 for this task, writing concrete answers — not "fast" but a number; not "cheap" but a volume estimate.
3. Based on the checklist, choose a starting model tier (frontier-class vs. small/fast-class) and name one real model in that tier you'd start with.
4. Pull 5-10 real or realistic inputs and manually spot-check the model's output against the quality bar you wrote down, following Core Concept 4.
5. Write one paragraph explaining your choice: task, quality bar, why this tier, and what the spot-check showed.

## Verify your work

- You can point to a written quality bar for the task that says what a correct output contains, not just "good quality."
- You multiplied per-request cost by real or realistic daily volume before deciding, and can state the resulting number.
- You checked context length and modality/tool-calling needs before judging output quality, not after.
- You ran at least 5 real inputs through the chosen model and checked each output against the quality bar, rather than trusting a single example.
- You can explain, in one paragraph, why you didn't need the most capable model available — or why you did.

## Review questions

- What is the practical difference between a frontier-class model and a small/fast-class model, in terms of both capability and cost?
- Why should context length and modality support be checked before comparing output quality, not after?
- Why does a cost-per-request number that looks negligible in a demo matter more at production volume?
- For the support-ticket summarization example, what specifically about the task made a small/fast-class model a reasonable starting choice?
- What is the risk of choosing a model based on general reputation rather than a checklist specific to your task?
