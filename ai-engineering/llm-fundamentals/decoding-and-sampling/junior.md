# Decoding and Sampling — Junior

<!-- level-focus -->
At junior level, focus on this question:

> Given the same prompt run three times, can you explain why the outputs differ, and predict how changing temperature, top-k, or top-p will change them?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core Concept 1 — The Model Outputs a Distribution, Not an Answer

A common beginner mental model is wrong in a way that causes real confusion: an LLM does not "know" the next word and print it. At every step, the model produces one number — called a **logit** — for every token in its vocabulary (commonly 50,000 to 200,000 entries, depending on the model's tokenizer). A logit is an unnormalized score: higher means the model considers that token more likely to come next, but the raw numbers aren't probabilities and don't sum to anything meaningful on their own.

**Softmax** turns the full list of logits into a proper probability distribution — every value between 0 and 1, all values summing to 1:

```
P(token_i) = exp(logit_i) / sum_j( exp(logit_j) )
```

So for the prompt `"The weather today is"`, the model doesn't decide on `"sunny"`. It produces a probability for *every* token in its vocabulary being next — `"sunny"` might get 0.42, `"cloudy"` 0.21, `"rainy"` 0.08, `"purple"` 0.0000003, and so on for all 100,000+ entries. **Decoding** is the separate step that turns this distribution into one chosen token. Everything in this file is about how that choice gets made, because different choices produce very different output from the exact same distribution.

## Core Concept 2 — Greedy Decoding: Always Take the Top Token

The simplest possible decoding strategy: at every step, pick the token with the highest probability (`argmax`). This is **greedy decoding**.

```
Step 1: P("sunny")=0.42, P("cloudy")=0.21, P("rainy")=0.08, ... → pick "sunny"
Step 2: (given "...today is sunny") pick highest-probability next token
...repeat until an end-of-sequence token or length limit
```

Greedy decoding is fully **deterministic** — the same prompt, the same model, the same weights always produce the same output, every time. That determinism is genuinely useful (predictable, easy to debug, cheap — no randomness machinery needed). Its weakness is also structural, not incidental: always taking the single most-likely token tends to produce text that's flat, generic, and prone to repetition loops (a model that starts repeating a phrase often keeps repeating it, because "repeat the last phrase" becomes the highest-probability continuation once it starts). Greedy decoding is a genuinely good default for tasks with one correct answer; it is a poor default for anything where you want variety.

## Core Concept 3 — Temperature: Scaling the Distribution Before Sampling

**Temperature** (`T`) is a single number that reshapes the probability distribution before a token is sampled from it, by dividing every logit by `T` before applying softmax:

```
P(token_i) = exp(logit_i / T) / sum_j( exp(logit_j / T) )
```

Concretely, take three candidate tokens with logits `A=4.0`, `B=3.0`, `C=1.0`:

| Temperature | Scaled logits (logit / T) | Resulting probabilities | Effect |
|---|---|---|---|
| `T = 0.5` | `8.0, 6.0, 2.0` | `A=0.88, B=0.12, C=0.002` | Sharper — the leader dominates even more than at T=1 |
| `T = 1.0` | `4.0, 3.0, 1.0` (unchanged) | `A=0.71, B=0.26, C=0.04` | The model's raw, unmodified distribution |
| `T = 2.0` | `2.0, 1.5, 0.5` | `A=0.55, B=0.33, C=0.12` | Flatter — the underdogs become much more competitive |

The pattern: **temperature near 0 pushes the distribution toward a single spike, approaching greedy decoding in the limit** (in fact `T=0` is typically implemented as greedy decoding directly, since dividing by 0 is undefined). **`T=1.0` samples from the model's distribution exactly as trained.** **`T` above 1 flattens the distribution**, giving low-probability tokens a real chance of being picked — more surprising, more varied, and past a certain point, less coherent.

Temperature does not change *which* tokens exist in the distribution or add any new information — it only changes how sharply peaked or flat the existing distribution is before a token is drawn from it.

## Core Concept 4 — Top-k: Only Consider the k Best Candidates

**Top-k sampling** truncates the candidate pool to the `k` highest-probability tokens, sets every other token's probability to zero, and renormalizes the remaining `k` so they sum to 1 before sampling. `top_k=40` is a common default: only the 40 most-likely next tokens are ever eligible, no matter how long the vocabulary's tail is.

This directly guards against one specific failure: sampling with a nonzero temperature over the *full* vocabulary means even a token with 0.0001% probability has some chance of being picked, and over a long generation, a rare enough event will eventually happen — producing a bizarre, out-of-place token. Top-k puts a hard ceiling on how deep into the tail sampling is allowed to reach.

Its weakness is that `k` is fixed regardless of context. When the model is very confident (one token at 0.9, the rest negligible), `k=40` still keeps 40 candidates around, 39 of which were never realistic choices. When the model is genuinely uncertain (probability spread thinly across hundreds of plausible tokens), `k=40` may cut off legitimate options that deserved a chance.

## Core Concept 5 — Top-p (Nucleus Sampling): Adapt the Pool to Confidence

**Top-p sampling** (also called **nucleus sampling**) fixes exactly that weakness. Instead of a fixed count, it takes the smallest set of tokens whose cumulative probability exceeds a threshold `p`, and samples only from that set.

Compare two situations with `p = 0.8`:

**Confident distribution** (model is sure what comes next):
```
A=0.50, B=0.30, C=0.10, D=0.05, E=0.05, ...
Cumulative: A→0.50, A+B→0.80  ← threshold crossed after 2 tokens
Nucleus = {A, B}
```

**Uncertain distribution** (model is spreading its bets):
```
A=0.15, B=0.13, C=0.12, D=0.11, E=0.10, F=0.09, ...
Cumulative crosses 0.80 only after ~7-8 tokens
Nucleus = {A, B, C, D, E, F, G, H}
```

The candidate pool **shrinks automatically when the model is confident and grows automatically when the model is uncertain** — which is exactly the adaptiveness a fixed `top_k` cannot provide. `top_p = 0.9` is a common default and is frequently used together with a moderate temperature rather than as a replacement for it — the two controls answer different questions: temperature reshapes the distribution's sharpness, top-p decides how much of that (reshaped) distribution is eligible to be sampled from at all.

## The Full Pipeline

```mermaid
flowchart LR
    Logits["Raw logits<br/>(one score per vocab token)"] --> Temp["Divide by temperature"]
    Temp --> Filter["Filter: top-k / top-p"]
    Filter --> Norm["Renormalize to sum to 1"]
    Norm --> Sample["Sample a token"]
    Sample --> Token["Next token emitted"]
```

Every generated token goes through this pipeline once. The loop repeats — feeding the new token back in as part of the context — until an end-of-sequence token is produced or a length limit is hit.

## Worked Example: Same Prompt, Three Temperatures

Prompt: `"Write one sentence about the ocean."` Run three times at each setting.

| Setting | Behavior across 3 runs | Why |
|---|---|---|
| `T = 0` (greedy) | Identical sentence every single run, e.g. *"The ocean is a vast body of saltwater that covers more than seventy percent of Earth's surface."* | No randomness in the pipeline at all — argmax always picks the same token given the same input |
| `T = 0.7` | Three different but all coherent, sensible sentences — different facts emphasized, different phrasing, no grammar breakdown | Distribution is sampled with moderate sharpness — enough variety to avoid repetition, not enough flattening to destabilize word choice |
| `T = 1.2` | Sentences start drifting — unusual word choices, run-on structure, sometimes a sentence that trails into near-nonsense by the end | Distribution is flattened enough that low-probability, poor-fit tokens get picked regularly, and each poor token shifts the context for the next prediction, compounding the drift |

This is the core intuition to carry forward: **temperature 0 is reliable but dull and identical every time; a moderate temperature adds useful variety while staying coherent; a high temperature trades coherence for novelty, and past some point that trade stops being worth it.**

## Common Mistakes

| Mistake | Why it hurts | Fix |
|---|---|---|
| Assuming higher temperature always means "better" or "smarter" output | Temperature only controls randomness, not quality or intelligence — past a point it actively degrades coherence | Pick temperature based on whether the task needs one right answer or a variety of plausible ones (more in `middle.md`) |
| Treating `T=0` as a guarantee of identical output forever, on any provider, any time | True in a strict theoretical sense for a single deterministic pipeline; real-world API-served models can still show tiny run-to-run variance | Understand the caveat exists — the mechanism is a senior-level topic, not something to solve at this stage |
| Using top-k and top-p as if they're the same knob | They filter differently — fixed count vs. adaptive cumulative mass — and produce different candidate pools from the same distribution | Know which one is active in whatever tool or API you're using, and what its default value is |
| Not noticing that `top_p=1.0` or an unset `top_k` means "no filtering at all" | Silently sampling from the model's full raw distribution when you thought you'd constrained it | Check the actual default values in the API or tool you're using — don't assume |
| Blaming "the model is unreliable" when the real cause is greedy decoding producing repetitive loops | Greedy decoding getting stuck repeating a phrase is a known, structural failure mode, not a model defect | Recognize the repetition pattern and switch to nonzero temperature or add a repetition penalty (`middle.md`) |

## Apply it

1. Pick a tool you can run sampling parameters through directly — a hosted playground (OpenAI Playground, Anthropic Console), a local model via Ollama, or a `transformers`/API script.
2. Write a short, open-ended prompt (one or two sentences of instruction, not a math problem with a single correct answer).
3. Run it three times at `temperature=0`, three times at `temperature=0.7`, and three times at `temperature=1.2` (or the highest value your tool allows near that), keeping every other parameter fixed.
4. Record all nine outputs. Note which set is identical across runs, which set varies while staying coherent, and which set starts to lose coherence.
5. Repeat once more, this time holding temperature fixed at `0.7` and varying `top_p` between a low value (e.g. `0.5`) and `1.0` (or `top_k` between `10` and disabled/very high). Note how the variety of outputs changes even though temperature never moved.

## Verify your work

- You can point to a specific run where `T=0` produced identical output across all three attempts.
- You can point to a specific run where `T=1.2` (or your tool's high end) produced a visibly less coherent output than `T=0.7`.
- You can explain, without looking it up, what temperature actually does mathematically (divides logits before softmax) rather than just "makes it more random."
- You can state the difference between top-k and top-p in one sentence each, and say which one your tool defaults to.
- You changed `top_p` (or `top_k`) while holding temperature fixed and observed a real difference in output variety.

## Review questions

- What is the difference between a logit and a probability, and what operation converts one into the other?
- Why is greedy decoding deterministic, and what specific failure mode is it prone to as a result?
- What does temperature mathematically do to the logits, and what happens to the distribution as temperature approaches 0 versus as it goes above 1?
- Why does top-p sampling adapt its candidate pool size automatically, in a way that a fixed top-k cannot?
- If you ran the exact same prompt at `temperature=0` five times and got five different outputs, what would that tell you about your assumptions?
