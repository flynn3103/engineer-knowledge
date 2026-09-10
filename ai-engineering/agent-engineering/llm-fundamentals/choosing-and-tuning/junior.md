# Choosing and Tuning — Junior

<!-- level-focus -->
At junior level, focus on this question:

> Can you run the eligibility gates that eliminate models outright, then match your task to a model family by what that family is built for?

---

## Step 1 — eligibility gates (before any quality comparison)

These are yes/no checks that disqualify models; there's no point comparing quality among ineligible candidates:

- **Modality**: does the task need image/audio/video input? Text-only models are out.
- **Tool calling**: does the workflow need function/tool calling? Weak or absent support is disqualifying for agents.
- **Structured output**: does the task need reliable JSON/schema output? Check for native support.
- **Context length**: does the input (plus output room) fit? Check worst-case, not average.
- **Deployment constraints**: data residency, self-hosting requirement, region availability — regulatory gates that override everything else.
- **Budget ceiling**: a hard per-token cap eliminates above-ceiling models regardless of quality.

## Step 2 — families and their design intent

Compare *families* by what they optimize for — specific versions change monthly, design intent is durable:

| Family | Design intent | Typical fit |
|---|---|---|
| **Anthropic Claude** | Careful instruction-following, long-context work, agentic tool use, nuanced writing; strong safety posture | Coding assistants, agent workflows, document analysis, tasks needing reliable instruction adherence |
| **OpenAI GPT (+ Codex line)** | Broad general capability and ecosystem breadth; the Codex line is purpose-built for coding and coding-agentic work (terminal, multi-file edits) | General-purpose apps, coding agents, broad ecosystem/tooling needs |
| **Google Gemini** | Very long context windows, native multimodality, integration with Google's ecosystem | Massive-document tasks, video/image-heavy apps, Google-stack shops |
| **Zhipu GLM** | Strong bilingual (Chinese/English) capability, competitive pricing, open-weight variants available | China-market apps, bilingual workloads, cost-sensitive deployments wanting open weights |
| **Open-weight (Llama, Qwen, Mistral, DeepSeek)** | Self-hostable weights: data control, flat cost at volume, fine-tuning freedom; frontier-adjacent at best | Residency-sensitive data, high-volume cost control, on-prem requirements, customization |

- Read the intent column as "what the maker optimizes," not a quality ranking. Families compete within overlapping ranges; the intent tells you where each is *at home*.
- Within any family: bigger/frontier variants for hard reasoning and ambiguity; small/fast variants for extraction, classification, routing (see [How LLMs Work — Middle](../how-llms-work/middle.md) on distillation — a purpose-built small model often beats a generic big one on narrow tasks).

## Step 3 — the four-question fit check

For surviving candidates: What does "good enough" mean for this task? How fast must it answer? What does it cost at real volume? Which candidate's design intent matches?

## Common Mistakes

- **Choosing by benchmark headline.** Capability peaks ≠ your task's reliability; only your own cases test your task.
- **Ignoring an eligibility gate until after selection.** Discovering missing tool-calling support after integration wastes the entire evaluation.
- **Treating families as interchangeable.** Each is at home in different terrain; the mismatch shows up as friction (weaker agentic behavior, worse bilingual handling), not failure.
- **Defaulting to the most famous model.** Reputation is evidence about prominence, not about your narrow task.

## Apply It

1. Write the eligibility gates for one real task; list the models each gate eliminates.
2. For the survivors, write one line each: which design intent matches this task, and why.
3. Run the four-question fit check and pick a starting candidate — writing down what would make you revisit the choice.

## Verify Your Work

- Gates were checked before quality, and eliminations are recorded.
- The family choice cites design intent, not a leaderboard.
- "Good enough," latency need, and volume cost are written down before comparing.

## Review Questions

- Why must eligibility gates precede quality comparisons?
- What is the Codex line's design intent, and what task shape is it at home with?
- Why is design intent more durable than benchmark numbers for family comparison?
