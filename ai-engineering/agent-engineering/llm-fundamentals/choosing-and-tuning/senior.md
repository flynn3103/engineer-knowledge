# Choosing and Tuning — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Can you judge when fine-tuning is genuinely the right tool, prepare data that meets its requirements, and measure success with the metrics that would actually catch a bad fine-tune?

---

## When fine-tuning is right — and when it's not

**Right:**
- **Style/format consistency at scale**: every output in your house voice, exact schema, no per-prompt examples needed — the behavior is *in the weights*, so prompts stay short and cheap.
- **Narrow-domain judgment**: classification/routing inside a specialized domain (medical triage categories, internal ticket taxonomies) where a smaller tuned model matches a big generic one.
- **Cost/latency reduction**: a tuned small model replacing a frontier API model on a high-volume narrow task — the fine-tune is how the small model earns the swap (see [How LLMs Work — Middle](../how-llms-work/middle.md)).

**Not right:**
- **Missing knowledge** → retrieval (rung 3). Fine-tuning teaches behavior, not facts; facts baked in via fine-tune go stale and can't be updated without retraining.
- **An unproven prompt.** If rung 1–2 hasn't measurably failed, fine-tuning is premature — you're paying to fix a prompt problem.
- **General capability hopes.** Fine-tuning narrows; it doesn't make a small model broadly smarter.

## Data requirements — the actual work

- **Quantity**: start at ~500–1,000 examples for a narrow task; behavior cloning on simpler patterns can work below that, but expect iteration. More diverse examples beats more duplicate examples.
- **Quality**: every example is a behavior lesson — inconsistent formats or contradictory judgments in the data teach inconsistency. Hand-audit a sample before training.
- **Distribution**: cover the input space — edge cases, ambiguities, and failures included, not just clean typical cases. A model tuned on happy-path data is happy-path-only.
- **Format**: same schema as production use (same prompt structure, same output format) — fine-tuning amplifies whatever pattern the data demonstrates.

## The factor checklist

| Factor | Decision |
|---|---|
| Base model | The smallest model that plausibly reaches the bar after tuning — the tune is the capability add |
| Method | **LoRA/PEFT** (low-rank adapters: cheap, fast, small artifacts) for most cases; full fine-tune only for wholesale behavior shifts |
| Data size & mix | 500–1,000+ diverse, audited examples; hold out 10–20% as a test set never seen in training |
| Hyperparameters | Start with provider defaults; the data quality matters more than the knobs |
| Cost & iteration loop | Budget for 2–4 tuning iterations — the first run is a baseline, not a deliverable |

## Metrics — how you know it worked (or broke)

- **Task metric on held-out data**: your task's own measure (accuracy, exact-format rate, grader score) on the held-out split. This is the headline number — nothing else counts if this didn't move.
- **Comparison against the incumbent**: tuned small model vs. the current frontier/prompt setup on the same eval set — quality delta, cost delta, latency delta (the bake-off from [Middle](middle.md), rerun with the tuned model as a candidate).
- **General-ability regression check**: run a few *out-of-domain* prompts — heavy tuning narrows the model; confirm it didn't forget how to handle the odd request your app still routes to it.
- **Consistency metrics**: for style/format tuning, the actual goal is variance reduction — measure format-violation rate across N runs (the rate-based testing from [Temperature and Sampling — Senior](../temperature-and-sampling/senior.md)).
- **Operational metrics**: p95 latency and cost per 1k calls — the numbers the swap decision was supposed to improve.

## Common Mistakes

- **Fine-tuning to add knowledge.** The most common wrong rung: facts go stale inside weights, and retrieval would have been cheaper, fresher, and auditable.
- **Dirty training data.** Inconsistent examples teach inconsistency perfectly; the model faithfully reproduces your data's mess.
- **No held-out split.** Evaluating on training data reports memorization, not learning — the tune looks great until production.
- **Skipping the regression check.** The tuned model nails the target task and silently got worse at everything else your app still asks it.
- **One tuning run, judged final.** The first run calibrates expectations; plans should assume iteration.

## Apply It

1. For your fine-tune candidate, write which "Right" box it checks and why rungs 1–3 measurably failed — if you can't, stop here.
2. Assemble and audit 50 random training examples for format/judgment consistency; fix the data before any training run.
3. Define the metric set before training: task metric on held-out, incumbent comparison, out-of-domain checks, format-violation rate.
4. After the first run, compare against the incumbent on all four — and decide iterate/stop from the numbers.

## Verify Your Work

- The fine-tune's justification names a behavior goal, not a knowledge goal.
- Training data passed a consistency audit and includes edge cases, with a held-out split reserved.
- Success is claimed with the pre-declared metric set, including an out-of-domain regression check.

## Review Questions

- Why can't fine-tuning substitute for retrieval on a knowledge task?
- What does the out-of-domain regression check protect against, and why does tuning cause it?
- Why is held-out evaluation the headline metric and training-set performance almost meaningless?
