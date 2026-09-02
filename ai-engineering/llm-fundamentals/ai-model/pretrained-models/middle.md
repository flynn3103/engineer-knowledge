# Pretrained Models — Middle

<!-- level-focus -->
At middle level, focus on this question:

> For a specific feature — a raw text-completion/autocomplete capability versus a conversational assistant — how do you decide between a base model and an instruct/chat model, and what specific, observable failure appears when you choose wrong?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core Concept 1 — The Decision Isn't "Which Is Better," It's "Which Matches the Task Shape"

A junior-level pass identifies what a model *is*. A middle-level pass has to decide what to *build with*, and the base-vs-instruct choice is a real design decision with a concrete failure mode on each side, not a default to reach for out of habit.

The question that resolves it: **does the feature need the model to continue something, or to respond to something?**

| Task shape | Example feature | Right default |
|---|---|---|
| Continues a document the user is already writing | Code autocomplete, inline text completion, "finish this sentence" | Base model, or a completion-tuned variant |
| Responds to a discrete request as a turn in a conversation | Support chatbot, "summarize this document" button, Q&A assistant | Instruct/chat model |
| Structured extraction from unstructured input | "Pull the invoice number and date from this text" | Instruct/chat model — you need it to follow a format, not continue the input |

This isn't a preference call. An instruct model has been trained, via SFT and RLHF/DPO, to treat every input as something to *respond to* — to add framing, explain itself, or stop early with a caveat. A base model has been trained to treat every input as something to *continue* — it has no notion of "this is a request" at all. Handing a continuation-shaped task to a response-trained model, or a response-shaped task to a continuation-only model, produces predictable, specific breakage.

## Core Concept 2 — Worked Example: The Wrong Choice, Two Ways

**Feature: inline code autocomplete.** The user is mid-way through writing a function; the product should complete it, matching their style, and stop at a sensible boundary.

Choosing an instruct/chat model for this:

```
Input (cursor position marked): "def calculate_total(items):\n    total = 0\n    for item in items:\n        <CURSOR>"

Instruct model output: "I'd be happy to help you complete this function!
Here's a suggested implementation:

    total += item.price

This adds each item's price to the running total. Let me know if you'd
like me to add error handling for missing prices."
```

This is a real, observable failure: the model wraps the completion in conversational framing, explains itself unprompted, and offers to keep talking — none of which belongs inline in an editor. It happens because RLHF/DPO explicitly rewarded exactly this kind of helpful, explanatory framing during alignment training; the model isn't malfunctioning, it's doing what it was aligned to do, applied to a task that doesn't want that behavior.

Choosing a base model for a conversational assistant:

```
Input: "How do I reset my password?"

Base model output: "How do I reset my password? How do I change my
email address? How do I delete my account? How do I contact support?
Frequently Asked Questions ..."
```

Same underlying failure as the junior-level example, now costing a real feature: the base model treats the question as the start of a document (an FAQ page) rather than something to answer, because nothing in pretraining taught it "this is a request, respond directly to it."

## Core Concept 3 — Under-Application and Over-Application Signals

- **Under-application signal**: a team defaults to an instruct/chat model for every LLM call in the product, including pure completion tasks, because it's the only kind of model anyone on the team has used. The tell is prompts full of instructions like "just output the completion, nothing else, no explanation" fighting against the model's alignment training instead of working with a model shape suited to the task.
- **Over-application signal**: a team reaches for a raw base model for a task that actually needs instruction-following or safety behavior (user-facing text generation from arbitrary user input) to save on cost or latency, and gets outputs with no refusal behavior, no consistent format, and no guardrail against the model continuing in an unintended direction — because none of that was ever trained in.

## Core Concept 4 — A Second, Crossing Axis: Open-Weight vs Closed

The base/instruct decision usually gets made together with a second one: **open-weight (self-hosted) or closed (API-only)**. They're independent axes — you can get an open-weight instruct model (Llama-Instruct) or a closed base-ish completion endpoint — but in practice they cluster, and the operational trade-off is concrete, not philosophical:

| | Open-weight (Llama, Mistral, DeepSeek) | Closed/API-only (GPT-4o/o1/o3 class, Claude, Gemini) |
|---|---|---|
| Data residency | Data never leaves your infrastructure | Every request goes to the provider |
| Operational burden | You run the serving infrastructure, scaling, and upgrades | Provider runs it; you send requests |
| Customization | Can fine-tune or modify the weights directly | Limited to prompting and provider-exposed fine-tuning APIs, if any |
| Frontier capability | Strong, but the largest closed models are typically ahead on the hardest tasks at any given time | Access to whichever model is currently the provider's best |
| Cost shape | Fixed infrastructure cost, scales with your own usage efficiency | Per-token pricing, scales directly and immediately with usage |

A feature with strict data-residency requirements (regulated user data that legally cannot leave your infrastructure) forces open-weight regardless of which model performs best in a benchmark. A team with no ML infrastructure and a tight deadline gets to a working feature fastest on a closed API. Neither is a universal default — the requirement drives the choice, not a preference for one vendor's marketing.

## Core Concept 5 — Parameter Count Is Not a Capability Number

A common but wrong shortcut: assuming a larger parameter count means a strictly better or slower/more-expensive model. Parameter count tells you almost nothing on its own about capability, cost, or latency, because it says nothing about:

- **Training data quality and quantity** — a smaller model trained longer on a cleaner, larger corpus can outperform a larger model trained on less or noisier data.
- **Alignment quality** — two models of the same size can differ enormously in how well SFT and RLHF/DPO were executed.
- **Context length** — a model's advertised context window is a separate, orthogonal spec from its parameter count.
- **Serving efficiency** — architecture choices (attention implementation, quantization, mixture-of-experts routing that activates only a subset of parameters per token) mean two models with the same total parameter count can have very different real inference cost and latency.

DeepSeek's publicly documented efficiency work on V3 is a concrete, real example of this decoupling in practice: DeepSeek published a report describing how they achieved strong benchmarked capability with a training approach emphasizing efficiency, which is exactly the kind of publicly discussed case that should make you distrust "bigger number in the name = better model" as a heuristic. Treat parameter count as one input to a capacity estimate, never as the answer to "which model should I use."

## Core Concept 6 — Verification at Two Levels

**Unit level — does the chosen model type produce correctly-shaped output for the task in isolation:**

```python
# Completion task: base model should stop at a natural boundary,
# not append conversational framing.
response = base_model.complete(prompt, stop=["\n\n", "def "])
assert not response.lower().startswith(("here's", "i'd be happy", "sure!"))

# Chat task: instruct model should not just continue the question
# as if it were a document.
response = instruct_model.chat(user_message)
assert not response.strip().startswith(user_message.split("?")[0])
```

**Integrated-flow level — does the choice hold up inside the actual feature, not just in an isolated prompt test:**

- For autocomplete: type a realistic multi-line snippet into the actual editor integration and confirm the completion inserts cleanly with no explanatory text, at the latency budget the feature requires.
- For the assistant: run a short multi-turn conversation through the real chat interface and confirm the model tracks context across turns and doesn't need each turn re-explained — a property SFT and RLHF specifically train for and a base model does not have by default.

## Real-World Examples

- **A completion feature ships with an instruct model by default, and every suggestion needs post-processing to strip conversational preamble.** The team eventually swaps to a completion-tuned model and deletes the string-stripping code entirely — the preamble was never a formatting bug, it was the wrong model type for the task.
- **A support-assistant prototype is built on a base model to save cost, and it never once declines an out-of-scope or unsafe request** — because refusal behavior is something RLHF/DPO teaches, not something present by default. The team migrates to the provider's instruct/chat endpoint before any real user traffic reaches it.
- **A team assumes a newer, smaller model in a family is automatically worse than the older, larger one it's replacing, and skips evaluating it.** After finally running their own eval set, the smaller model matches or beats the larger one on their specific task, at a fraction of the latency — the parameter count difference did not predict the outcome.

## Common Mistakes

- **Fighting a model's alignment training with prompt instructions instead of choosing the model type suited to the task.** "Don't explain, just output the code" prompted at an instruct model works less reliably than using a model type that was never trained to explain in the first place.
- **Assuming every open-weight model ships alignment for free.** As at junior level, but now costing a real feature: deploying a base variant into a user-facing conversational feature without ever adding an SFT/RLHF-equivalent step.
- **Choosing open vs closed based on capability rumors instead of the feature's actual data-residency and operational constraints.** The constraint should drive the decision; capability comparisons matter only among options the constraint already allows.
- **Treating parameter count as a proxy for quality without running your own evaluation.** Two same-size models, or a smaller-vs-larger pair, can invert your assumption on your specific task.

---

## Apply it

1. Pick two real or hypothetical features in a product you know: one continuation-shaped (autocomplete, inline completion) and one response-shaped (assistant, summarizer, extractor). For each, state which model type — base or instruct/chat — the task shape calls for, using Core Concept 1's table.
2. For the continuation-shaped feature, write the exact prompt you'd send and the stop condition you'd use; predict what an instruct model would incorrectly add if used instead, before checking.
3. For the response-shaped feature, list the data-residency or operational constraints (if any) that would force an open-weight or closed choice regardless of capability.
4. Find two models — same family, different sizes if possible — and design a five-prompt evaluation set specific to one of your features. Note that you are treating parameter count as untested until you run it, not as a given answer.
5. Write the unit-level assertion and the integrated-flow check you'd use to verify each feature's model choice, following Core Concept 6.

## Verify your work

- You can state, for each of your two features, the specific observable failure the wrong model type would produce — not a vague "it wouldn't work as well."
- Your unit-level check catches the specific failure pattern (conversational preamble on a completion task, or document-continuation on a response task) rather than just checking the response is non-empty.
- Your open-vs-closed decision cites a concrete constraint (data residency, operational capacity, customization need), not a general capability preference.
- You ran (or designed and can justify not running) an evaluation comparing at least two models before concluding one is better, rather than inferring quality from parameter count alone.

## Review questions

- What specific, observable output distinguishes a task-shape mismatch (wrong model type for the job) from a genuinely broken prompt?
- Why does prompting an instruct model with "don't explain, just output the result" often work less reliably than choosing a completion-tuned model for that task?
- What is one constraint that would force an open-weight model choice even if a closed model scored higher on every capability benchmark?
- Why does parameter count alone fail to predict which of two models will perform better on a specific task?
- Give one example of a unit-level check and one example of an integrated-flow check for verifying a base-vs-instruct model choice.
