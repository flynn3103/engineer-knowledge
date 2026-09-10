# Tokens and Context — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Can you diagnose why long-context answers degrade, catch silent truncation bugs, and decide between long context and retrieval for a real workload?

---

## Effective context < advertised context

- A model accepting 200k tokens doesn't mean it *uses* 200k tokens well. Quality typically degrades as the window fills — attention over very long inputs gets less reliable.
- **"Lost in the middle"**: models recall the start and end of a long context better than the middle. Critical facts buried mid-document are the ones most often missed.
- Practical consequence: a long-context task that "fits" can still fail. Test at real lengths, not with short demo prompts.

## Truncation bugs — the silent failure

- Exceeding the window either errors (visible) or gets truncated by a client/SDK layer (invisible).
- The truncated case is the dangerous one: the model answers confidently from incomplete input. Nobody sees the missing half.
- Defensive design:
  - Count tokens before sending; fail loudly on overflow rather than truncating silently.
  - Decide and document *what* gets dropped when input must shrink (oldest history? middle chunks? least relevant tool output?).
  - Alert on input-length distribution shifts — a sudden rise toward the limit is a bug in progress.

## Long context vs. retrieval

- **Long context**: paste everything in. Simple, no infrastructure, preserves cross-document reasoning. You pay for all of it, every call, and quality degrades with size.
- **Retrieval (RAG)**: fetch the few relevant chunks. Cheap per call, scales with corpus size, keeps prompts small — but adds an infrastructure layer and fails when retrieval misses.
- Decision heuristic: a handful of stable documents → long context. A large or growing corpus, or cost-sensitive volume → retrieval. Mixed: static core in context (cached), long-tail via retrieval.
- The deeper decision framework lives in [RAG and Vector Decisions](../../context-management/rag-and-vector-decisions/).

## Common Mistakes

- **Assuming "it fit in the window" means the model read it well.** Middle-of-context facts are systematically weaker.
- **Discovering truncation from user reports.** Silent truncation must be made loud in code, or it ships as quality degradation.
- **Pasting a growing corpus into context because "the window is big now."** Cost scales linearly and quality degrades — the opposite of what you want at volume.
- **No per-length testing.** A prompt tuned at 500 tokens can behave differently at 50,000.

## Apply It

1. Take one long-input case and move the critical fact to the start, the middle, and the end of the input — compare answers to see the lost-in-the-middle effect on your own model.
2. Add an overflow check that fails loudly, and document the drop-oldest/drop-least-relevant policy your app actually uses.
3. For one workload, compute the cost of full-context-per-call vs. retrieval of top-k chunks, and note where the crossover sits.

## Verify Your Work

- Input length is measured and enforced in code, with a documented truncation policy.
- Critical instructions/facts are placed at the edges of long inputs, not the middle.
- The long-context-vs-retrieval choice for your workload has a stated cost and quality rationale.

## Review Questions

- What is "lost in the middle," and where should critical facts go in a long input?
- Why is silent truncation worse than a hard error, and what's the defense?
- What workload characteristics favor long context over retrieval, and vice versa?
