# Context Fundamentals — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Before a turn runs, can you decide how many tokens each part of the context is allowed to use — and enforce it — instead of discovering the budget was blown after the fact?

---

## Set a per-turn budget

Pick a hard ceiling per category, not just a total. Example for a 128k-window agent:

| Category | Budget | Why capped here |
|---|---|---|
| System prompt | ~2k | Fixed cost, paid every turn — keep it lean. |
| Tool schemas | ~4k | Grows with every tool added; audit it, don't let it silently creep. |
| Conversation history | ~30k | Summarize/drop older turns past this. |
| Retrieved content | ~20k | Cap search/RAG results — more retrieved ≠ better answer (see [RAG and Vector Decisions](../rag-and-vector-decisions/)). |
| Headroom for response + reasoning | remainder | The model needs room to think and answer, not just read. |

- Without an explicit cap per category, one category (usually retrieval, dumping "top 50 results") silently eats the others' room.
- A budget forces a decision at design time — "what happens when retrieval alone would exceed 20k tokens?" — instead of an unbounded prompt that happens to work in a demo and breaks in production.

## Placement matters, not just quantity

Models attend to context unevenly — content in the middle of a long context is used worse than content at the start or end, an effect sometimes called "lost in the middle." ([Liu et al., "Lost in the Middle" (2023)](https://arxiv.org/abs/2307.03172))

- Put the current user question and the most decision-critical instruction near the **end** of the prompt, closest to where generation starts.
- Put stable, rarely-changing material (system prompt, tool schemas) at the **start**, not interleaved with volatile content — this also helps prompt caching (next section).
- Don't bury the one constraint that must not be violated ("never issue a refund over $500 without approval") in the middle of a long document dump. State it near the instruction, and consider restating it near the end too.

## Prompt caching and prefix stability

Many providers cache the "prefix" of a prompt — the part that's identical to a previous call — so repeated calls with the same system prompt + tool schemas + early history are cheaper and faster. This only works if that prefix doesn't change turn to turn.

- Put the system prompt and tool schemas first, and keep them byte-identical across turns of the same conversation.
- Don't inject a timestamp, a random ID, or reordered content into the "stable" part of the prompt — it invalidates the cache for every token after it, not just the one that changed.
- Appending new content (new turn, new tool result) to the *end* preserves the cached prefix; rewriting or reordering earlier content destroys it.

## Truncation that keeps meaning

When a category exceeds its budget, cutting matters as much as cutting:

- **Truncate by boundary, not by character count.** Cut at a paragraph, function, or message boundary — never mid-sentence or mid-JSON-object.
- **Truncate the least relevant, not just the oldest.** For retrieved search results, drop the lowest-ranked hits first, not an arbitrary "keep the first N."
- **Say what was cut.** If history is summarized or truncated, the summary should say "12 earlier turns summarized" so the model (and a human reviewing the transcript) knows information was dropped, rather than silently vanishing.

## Comprehension check

- Why does an explicit per-category token budget beat "just try to keep it under the window limit"?
- What does "lost in the middle" mean, and what's one concrete change to prompt layout that mitigates it?
- Why does injecting a timestamp into the system prompt hurt performance even if the timestamp itself is small?
- Give one bad and one good way to truncate a set of 50 retrieved search results down to 10.
