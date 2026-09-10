# How LLMs Work — Junior

<!-- level-focus -->
At junior level, focus on this question:

> Can you explain what the model is doing at each step of generating an answer — and why that explains hallucination, no learning mid-chat, and what "7B" means?

---

## The next-token loop

- An LLM generates text one **token** at a time (a token ≈ ¾ of a word — see [Tokens and Context](../tokens-and-context/)).
- Each step: the model reads everything so far (your prompt + its own output so far), and predicts a probability for every token in its vocabulary of coming next.
- One token is picked from that distribution (how is [Temperature and Sampling](../temperature-and-sampling/)'s job), appended, and the loop repeats until an end condition.

```mermaid
flowchart LR
    P["Your prompt"] --> M["Model: score every possible next token"] --> T["Pick one token"] --> A["Append to output"]
    A --> M
    A -->|end token or limit| D["Done: answer"]
```

- Consequence: the model has no plan it's hiding. Long answers are just many single predictions, each conditioned on everything before it.

## Parameters — what "7B" or "70B" means

- A **parameter** is one adjustable number inside the model. **Weights** are the parameters learned during training — together they are "the model."
- "7B" means roughly 7 billion parameters. More parameters generally means more capability — and more memory, more cost, and slower generation.
- When you call an API, you're sending tokens into a frozen block of numbers and reading tokens out. That's the whole product.

## Training vs. inference — the model never learns from your chat

- **Training** (once, offline, expensive): adjusting the parameters until next-token predictions match human text.
- **Inference** (every API call you make): parameters are **frozen**. Nothing updates.
- Correcting the model mid-conversation helps only within that conversation — it re-reads your correction as context each turn. The next fresh conversation starts from zero.
- "Memory" features in products are a workaround: earlier conversation text stored and re-inserted into context, not learning.

## Hallucination is structural, not a bug

- The model's only job is: *given these tokens, what's the most plausible continuation?*
- Ask about something outside its knowledge and it still must produce plausible-looking tokens — a confident-sounding answer is just the most statistically likely text, not a verified fact.
- It has no built-in "I don't know" boundary unless trained or instructed to have one, and even then the pull toward plausibility remains.
- Practical defense: give it the facts in the prompt (retrieval, tool results), and verify outputs where being wrong is expensive.

## Common Mistakes

- **Treating the model as a database.** It generates plausible text; it doesn't look answers up. Facts it "knows" are compressed statistical patterns from training data, retrievable imperfectly.
- **Expecting a mid-chat correction to stick.** Parameters are frozen — the correction lives only in that conversation's context.
- **Reading "7B" as a quality score.** Parameter count bounds capability but doesn't determine it — training data and method matter too.
- **Being surprised the model answered confidently and wrongly.** Plausibility is the objective; confidence in the text is not confidence about the world.

## Apply It

1. Take one real prompt you use. Write out, token-idea by token-idea, what the loop does: read everything → score next token → append → repeat.
2. Find a model card for a model you use. Note the parameter count, and what the card says about training-data cutoff.
3. Test frozen weights: tell the model a made-up fact, correct it, start a fresh conversation, ask again — confirm it "forgot."

## Verify Your Work

- You can explain the loop without the words "understands" or "thinks."
- You can say what parameters and weights are, and what 7B counts.
- You can explain hallucination as a consequence of the objective, not model sloppiness.

## Review Questions

- Why does correcting the model mid-conversation not teach it anything?
- Why can a model state something false with full confidence?
- What does "70B" literally count, and what does it predict about cost and speed?
