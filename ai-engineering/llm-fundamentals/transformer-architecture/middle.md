# Transformer Architecture — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Given a concrete latency or cost constraint — for example, sub-300ms time-to-first-token on conversations that run past 20,000 tokens — which decoder-only architecture variant should you choose, and can you justify it with the KV cache memory math rather than a vendor's marketing page?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core Concept 1 — Why Decoder-Only Won for Chat and Completion

The junior guide named three architecture families. In production chat and completion products — the category nearly every LLM API serves today — decoder-only has effectively become the default, and it's worth understanding why, not just accepting it:

- **Autoregressive generation needs causal masking anyway.** A chat product generates a response one token at a time, and each new token must only depend on what came before it — that's exactly what a decoder-only model's masking already guarantees. An encoder-decoder model (T5-style) would need its decoder half to do the same job, so the encoder half is extra machinery that only pays for itself when there's a genuinely distinct "input" and "output" with different statistical structure (translation is the classic case: source and target are different languages).
- **One architecture family simplifies serving.** A decoder-only model has one set of weights, one attention pattern, and one KV cache shape to reason about for every request — system prompt, conversation history, and generation all flow through the same mechanism. An encoder-decoder deployment has to serve two different components with different compute profiles, which complicates batching and autoscaling for comparatively little benefit in an open-ended conversational setting where there's no clean input/output split.
- **Encoder-only (BERT-style) was never a generation architecture.** It produces a representation of a fixed input, not a sequence of new tokens — it's the right tool for classification or embedding, not for chat, and comparing it to decoder-only for a generation product is comparing tools built for different jobs.

The practical upshot: if your product's job is "take a conversation, produce the next message," decoder-only is not one option among equals — it's the architecture built for that exact causal-masking requirement, which is why GPT, Llama, Claude, and Gemini all converged on it for their chat-facing models.

## Core Concept 2 — The KV Cache: What It Is and Why It Exists

Generating a response token-by-token naively would mean, for every new token, recomputing attention over the *entire* prefix (system prompt + conversation history + everything generated so far) from scratch — an O(n²) cost per token that gets worse as the conversation grows. The **KV cache** avoids this: since the key and value vectors for every earlier token don't change once computed (they only depend on that token and the tokens before it, which are fixed), the model computes each token's K and V vectors once and caches them. Generating the next token only requires computing Q, K, V for the *new* token and attending it against the cached K/V of everything before it.

This is a straightforward trade: **memory for compute**. You pay GPU memory to store every past token's K and V vectors, for every layer, in exchange for not recomputing them. It's why generation has two distinct phases with very different cost profiles:

- **Prefill** — processing the input prompt for the first time, computing K/V for every prompt token in parallel. Compute-bound.
- **Decode** — generating each subsequent token one at a time, reading the whole KV cache and appending one new entry to it. Memory-bandwidth-bound, and this is the phase where the KV cache's size directly determines both latency and how many concurrent requests fit in GPU memory (the senior guide covers this as a system-level constraint).

## Core Concept 3 — Dense vs. Mixture-of-Experts (MoE)

A **dense** model uses every parameter for every token — if it has 70B parameters, every forward pass touches all 70B. A **Mixture-of-Experts (MoE)** model replaces the feed-forward block in each layer with several parallel "expert" feed-forward blocks and a small router that picks a subset (often 2 of 8) to actually run for each token. Mixtral (8x7B, 2 experts active per token) and DeepSeek-V3 (a much larger, fine-grained MoE design) are public examples; GPT-4 has been widely reported, though not officially confirmed by OpenAI, to use an MoE architecture as well.

The trade-off:

| | Dense | MoE |
|---|---|---|
| Active compute per token | All parameters used | Only the routed experts' parameters used — can be a small fraction of total parameters |
| Total parameter count vs. active parameter count | Equal | Total can be many times larger than active — more capacity without proportionally more compute per token |
| Memory footprint | Proportional to parameter count | All experts must still be loaded into memory even though only a few run per token — memory cost tracks total parameters, not active parameters |
| Serving complexity | Straightforward batching | Routing adds complexity: different tokens in the same batch can route to different experts, complicating batching and load-balancing across GPUs |

MoE is attractive when you want more model capacity without a proportional increase in the compute (and therefore latency) per token — but it does not save memory the way it saves compute, and the routing logic is real added complexity in the serving stack, not just the model definition.

## Core Concept 4 — Attention Variants: MHA, GQA, MQA, and the KV Cache They Produce

The junior guide covered multi-head attention as parallel Q/K/V projections. What it didn't cover: the *key and value* projections don't have to have as many heads as the *query* projection, and shrinking them is one of the most direct levers on KV cache size.

- **Multi-Head Attention (MHA)** — the original design: the same number of K/V heads as Q heads. Every query head gets its own K/V head. Best quality per head, largest KV cache.
- **Grouped-Query Attention (GQA)** — introduced by Ainslie et al. and adopted starting with Llama 2's larger models (34B/70B) and continued in Llama 3 and Mistral: multiple query heads share one K/V head, in groups. Fewer K/V heads to cache, at a modest quality cost relative to full MHA, with quality much closer to MHA than to MQA.
- **Multi-Query Attention (MQA)** — the extreme case, originally proposed by Shazeer: *all* query heads share a single K/V head. Smallest possible KV cache for a given model size, at the largest quality cost of the three.

The relationship that matters operationally: **KV cache size scales directly with the number of K/V heads**, not the number of query heads. Going from MHA to GQA to MQA doesn't change how many query heads the model has (that stays fixed by design) — it changes how many *separate* K/V heads need their own cached entries. Core Concept 6 works this out with real numbers.

**Sliding-window attention** is a related but different lever: instead of shrinking the number of K/V heads, it caps how far back each token can attend at all. Mistral 7B pairs GQA with a sliding window (a fixed window of recent tokens, rather than the full history) — beyond that window, older tokens are simply not attended to directly, which bounds the KV cache size independent of how long the conversation gets, at the cost of the model losing direct access to anything outside the window (long-range information has to propagate through intermediate layers instead of being attended to directly).

## Core Concept 5 — Under- and Over-Application Signals

- **Under-application**: shipping a full-MHA model for a high-concurrency, long-context product without ever computing what that costs in KV cache memory — the architecture "works" in a demo with one user and silently falls over (or forces tiny batch sizes) the moment real concurrent traffic with long conversations arrives. This is the failure mode Core Concept 6 walks through.
- **Over-application**: reaching for MQA, an aggressively small sliding window, or an MoE model on a low-QPS internal tool where GPU memory was never the constraint — you pay a real quality cost for a memory saving nobody needed, because nothing was actually measured before making the switch.

The signal in both directions is the same: architecture variant selection should follow from a measured constraint (concurrency, context length, latency budget), not from picking "the fancy new option" or "the safe default" without checking whether the constraint that variant addresses is actually present in your product.

## Core Concept 6 — Worked Scenario: Sub-300ms First-Token Latency on 20k-Token Conversations

**Constraint:** the product needs time-to-first-token under 300ms even on conversations that have grown past 20,000 tokens, at a concurrency high enough that GPU memory is a real limit, not a theoretical one.

Time-to-first-token is dominated by prefill — processing the full prompt before the first token can be generated — and by how much of the GPU's memory bandwidth is already committed to existing requests' KV caches sitting in memory. A model with a large KV cache per request leaves less memory (and often less effective bandwidth) for the concurrent requests competing for the same GPU, which is exactly what pushes first-token latency up under load even if a single isolated request looks fast in a demo.

Use the standard KV cache size formula, applied to an illustrative mid-size decoder-only model — 32 layers, head dimension 128, serving a 20,000-token conversation, weights and cache in fp16 (2 bytes per value):

```
KV cache bytes = 2 (K and V) × num_layers × num_kv_heads × head_dim × seq_len × bytes_per_param
```

| Variant | num_kv_heads | KV cache for this one 20k-token request |
|---|---|---|
| Full MHA (32 query heads, 32 KV heads) | 32 | 2 × 32 × 32 × 128 × 20,000 × 2 bytes ≈ **10.5 GB** |
| GQA (32 query heads, 8 KV heads — a 4:1 group size) | 8 | 2 × 32 × 8 × 128 × 20,000 × 2 bytes ≈ **2.6 GB** |
| MQA (32 query heads, 1 KV head) | 1 | 2 × 32 × 1 × 128 × 20,000 × 2 bytes ≈ **0.33 GB** |

The query head count never appears in this formula — it's `num_kv_heads` that drives cache size, which is exactly why GQA and MQA exist as a lever separate from "how many attention heads does the model have."

On a GPU with, say, 80GB of memory, most of it already committed to model weights, a handful of full-MHA requests at 20k tokens each can exhaust the memory left for KV cache entirely — forcing either a tiny concurrent batch size (requests queue behind each other, and time-to-first-token for a queued request includes however long it waits) or an out-of-memory failure. The same GPU serving the GQA variant fits roughly 4x as many concurrent 20k-token conversations in the same KV cache budget, which is what actually keeps time-to-first-token low under real concurrent load — not the model's raw compute speed, which barely differs between the three variants at prefill time.

This is why a GQA (or, for even tighter memory budgets, MQA or sliding-window) decoder-only model beats a full-MHA model on this specific constraint: the constraint is about how many long-context requests fit in memory *simultaneously*, and that's a KV cache problem, not a raw-FLOPs problem.

## Core Concept 7 — Verification: Measure, Don't Assume

None of the reasoning above substitutes for measurement. Verify at two levels:

**Unit level — the KV cache math for your actual model and workload:**

- Get the real `num_layers`, `num_kv_heads`, and `head_dim` for the model you're evaluating (published in its model card or config, not guessed by analogy to the illustrative example above).
- Compute KV cache size at your product's real p95 conversation length and intended concurrency, not a demo-sized input.

**Integrated-flow level — against a running deployment under realistic load:**

```bash
# Load test with concurrent long-context requests, not one request at a time
# (tool-specific; vLLM and TensorRT-LLM both expose token-level latency metrics)
# Measure directly:
#   - time-to-first-token (TTFT) under N concurrent 20k-token requests
#   - GPU memory actually consumed by KV cache at that concurrency
#   - whether requests start queuing before memory is nominally exhausted
```

A model that looks fast in a single-request benchmark and a model that meets a 300ms TTFT target under real concurrent long-context load are different claims — the first tells you almost nothing about the second. If measured TTFT under load doesn't meet the budget, the fix is one of: shrink `num_kv_heads` (GQA/MQA), cap context length, reduce concurrent batch size, or move to sliding-window attention — and each of those trade-offs should be re-measured, not assumed to work from the math alone, because real serving stacks add overhead (scheduling, memory fragmentation) the formula doesn't capture.

## Common Mistakes

- **Picking an attention variant from a vendor's headline feature list, not from the KV cache math for your own model and workload.** "Uses GQA" doesn't tell you the group size or the actual memory savings for your specific `num_layers` and `head_dim`.
- **Benchmarking latency with one request at a time.** Time-to-first-token under real concurrency is often dominated by memory contention between requests, which a single-request benchmark never exercises.
- **Treating MoE as a pure win because "active compute is lower."** Memory footprint tracks total parameters, not active parameters — an MoE model can need more GPU memory than a dense model with the same active-compute cost per token.
- **Assuming a bigger group size (more query heads sharing a K/V head) is always fine because "GQA is standard now."** The quality cost of GQA grows as the group size grows; a 4:1 group and a 16:1 group are different trade-offs, not the same feature.
- **Reaching for sliding-window attention without checking whether the product actually needs long-range recall past the window.** Bounded memory is a real win only when nothing important in the conversation regularly falls outside the window.

## Apply it

1. Pick a real decoder-only model you have access to (open-weight, so you can read its config) and record its `num_layers`, `num_kv_heads`, `num_attention_heads`, and `head_dim`.
2. Using the formula in Core Concept 6, compute its KV cache size at your product's real p95 conversation length, in bytes and then GB.
3. Recompute the same formula assuming the model instead used MQA (`num_kv_heads = 1`), and state the ratio of memory saved.
4. Load test the model (or a comparable one) with at least 10 concurrent requests at that same conversation length and record measured time-to-first-token and observed GPU memory used by the KV cache specifically.
5. Write one paragraph stating whether, for your actual product's constraint, GQA/MQA/sliding-window would be worth its quality cost — citing the measured numbers from step 4, not the math from step 2 alone.

## Verify your work

- You can state, for a specific model, its real `num_kv_heads` (not assumed from its total head count) and what that implies about its KV cache size relative to full MHA.
- You have a computed KV cache size, in GB, for your product's actual p95 sequence length and target concurrency — not a hypothetical one.
- You have measured (not estimated) time-to-first-token under concurrent load, and can state whether it meets your latency budget.
- You can explain, without notes, why the KV cache formula's `num_kv_heads` term is the lever GQA and MQA pull, while `num_attention_heads` (query heads) stays unchanged.
- You can name one product characteristic (conversation length, concurrency, or QPS) that would make sliding-window attention the wrong choice for a given product, not just the right one.

## Review questions

- Why does a decoder-only architecture's causal masking make it a natural fit for autoregressive chat generation, in a way an encoder-decoder architecture is not?
- What specific trade does the KV cache make, and which two serving-time costs does it move memory usage between?
- Why does an MoE model's memory footprint not shrink in proportion to its lower active-compute cost per token?
- In the KV cache size formula, why does reducing `num_kv_heads` reduce cache size while leaving `num_attention_heads` unchanged?
- What real-world measurement would tell you whether a GQA model actually solves a concurrent long-context latency problem, as opposed to just looking correct on paper?
