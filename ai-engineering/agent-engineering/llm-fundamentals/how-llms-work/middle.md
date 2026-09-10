# How LLMs Work — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Can you explain why a distilled small model beats a generic one of the same size, what quantization trades away, and when an open-weight model beats a hosted API?

---

## Distillation — a small model with a big model's behavior

- **Distillation** trains a small "student" model to imitate a large "teacher" model's outputs, rather than training on raw text alone.
- Why it works: the teacher's outputs are cleaner, more consistent training targets than messy human text. The student learns *behavior*, not just statistics.
- Practical consequence: a **distilled 8B model often beats a generic 8B model** on the tasks it was distilled for — at a fraction of the teacher's cost and latency.
- What it doesn't get you: the teacher's full knowledge and edge-case judgment. Distilled models inherit the teacher's blind spots, compressed.

## Quantization — trading precision for memory

- Parameters are stored as numbers. Full precision (e.g., 16-bit floats) uses ~2 bytes per parameter: a 7B model needs ~14 GB of memory.
- **Quantization** stores each parameter in fewer bits (8-bit, 4-bit): the same 7B model fits in ~7 GB or ~3.5 GB.
- Trade-off: output quality degrades slightly; aggressive quantization (very low bits) degrades noticeably, especially on reasoning-heavy tasks.
- Why you care: quantization is why a 7B-class model can run on a laptop or a cheap GPU, and why self-hosted small models are economically possible.

## Hosted API vs. open-weight

- **Hosted API** (Anthropic, OpenAI, Google, Zhipu): no infrastructure, always the newest models, pay per token. You give data to a third party; you don't control versions or availability.
- **Open-weight** (Llama, Qwen, Mistral, and GLM's open variants): download and run the weights yourself — full control, per-GPU flat cost, data stays inside your boundary. You own scaling, serving, and upgrades.
- Rule of thumb: frontier capability and speed-to-latest favor the API; data control, predictable cost at high volume, and fine-tuning freedom favor open weights.

## Common Mistakes

- **Assuming same parameter count = same quality.** A distilled or purpose-tuned 8B can outperform a generic 8B by a wide margin on its target tasks.
- **Quantizing a reasoning-heavy model to the lowest possible bits and blaming the model for worse answers.** Aggressive quantization is often the actual cause.
- **Choosing API vs. open-weight on quality alone.** Data-residency requirements, volume economics, and version control are usually the deciding factors.
- **Assuming "open weight" means open training data or a free license.** Weights being downloadable tells you nothing about the license terms or how it was trained.

## Apply It

1. For a task you're building: identify whether a distilled small model exists for it, and estimate the cost difference vs. a frontier API model.
2. Compute the memory needed for a 7B model at 16-bit, 8-bit, and 4-bit — confirm which hardware options that opens up.
3. List your app's constraints (data sensitivity, volume, version stability) and mark each as favoring hosted API or open weight.

## Verify Your Work

- You can explain distillation as "learning the teacher's behavior," and its limits.
- You can compute quantized memory needs and state the quality trade.
- Your API-vs-open-weight analysis cites at least one non-quality factor.

## Review Questions

- Why does a distilled 8B model often beat a generic 8B model?
- What does 4-bit quantization trade away, and what does it buy?
- Name two reasons besides model quality to choose an open-weight model.
