# Context Engineering — Middle

<!-- level-focus -->
At middle level, focus on this question:

> When a context assembly pipeline has more candidate content — retrieved chunks, conversation history, tool results — than fits its token budget, can you design and implement a priority policy that decides what's included, in what order, and what's dropped or compressed, and verify that the highest-relevance content survives truncation rather than an arbitrary or first-N cut?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core Concept 1 — Context Assembly Is a Pipeline, Not a Fixed Concatenation

A junior-level context has a fixed shape: one system prompt, one document, one question, always in the same order, always fitting comfortably. A real system's set of candidate sources is not fixed — it varies call to call:

- **Conversation history** grows every turn.
- **Retrieved document chunks** vary in count and size depending on what the retrieval step found (see [context-window's](../context-window/README.md) coverage of how history alone consumes budget; a dedicated RAG domain will cover chunking and retrieval strategy in depth).
- **Tool call results** (an API response, a database query result) arrive at unpredictable sizes.
- **Few-shot examples** may be added to steer output format.

All of these compete for the same token budget on every single call, and unlike the junior scenario, they don't reliably fit. A context assembly pipeline is the code that decides, on every call: what's a candidate for inclusion, how it's ranked, what the cutoff is, and what happens to what doesn't make the cut. Treating assembly as "concatenate everything the retrieval step returned" is the middle-level equivalent of the junior mistake of concatenating without delimiters — it works until the day it doesn't, and it fails silently (either an API error when the hard token limit is hit, or a context so bloated with low-relevance material that the actual answer gets buried).

## Core Concept 2 — Relevance Filtering and Ranking Before Inclusion

Not every retrieved chunk is equally useful, and including all of them is rarely free even when it technically fits the token budget: a large fraction of low-relevance content pushes the genuinely relevant content further from the question (Core Concept 4 in [junior.md](junior.md) covers why position matters), and it costs real tokens — latency and money — for content unlikely to change the answer.

Two common filtering strategies:

- **Top-N by relevance score.** A retrieval step (keyword search, vector similarity, or a re-ranking model) returns a relevance score per chunk. Sort descending, keep the top N chunks that fit the remaining budget.
- **Relevance threshold.** Keep any chunk whose score exceeds a fixed cutoff, regardless of how many that ends up being. This avoids forcing in a low-relevance Nth chunk just to hit a target count, but risks including zero chunks (or far too many) if the score distribution shifts.

In practice, most production pipelines combine both: a threshold to exclude clearly irrelevant results, then a top-N cap on what remains to respect the budget. Neither strategy works without a trustworthy relevance score in the first place — a retrieval step that returns chunks in arbitrary or recency order, with no score at all, gives the assembly pipeline nothing to rank on, and "top N" degrades into "first N," which is exactly the arbitrary cut this concept exists to avoid.

## Core Concept 3 — A Concrete Priority Policy

Ranking within one source (retrieved chunks) isn't enough once multiple *kinds* of sources compete for the same budget. A workable default policy, in priority order:

1. **System instructions and the current user turn — never dropped.** These define the task itself; dropping either produces a response to a different, undefined task.
2. **Recent conversation history — high priority, compressed before it's dropped.** The last few turns carry context the current question likely depends on; older turns are candidates for compression (Core Concept 5) rather than outright removal.
3. **Retrieved documents — ranked and truncated first when budget is tight.** These are supporting evidence, not the task definition; the tail of the ranked list is the correct place to cut.

Applied to a call with a fixed total budget, this produces a table like the one below — a RAG-backed support assistant with an 8,000-token working budget (a deliberately conservative cap the team set for cost and latency, well under the underlying model's much larger advertised window):

| Source | Tokens | Priority | Included at 8,000-token budget? |
|---|---|---|---|
| System instructions | 500 | 1 — never dropped | Yes |
| Reserved output | 800 | 1 — reserved always | Yes |
| Current user question | 50 | 1 — never dropped | Yes |
| Conversation history (last 4 turns) | 1,500 | 2 — compress before dropping | Yes |
| Retrieved chunks (top 6 of 12, ~800 tokens each) | 4,800 | 3 — ranked, tail truncated first | Yes (top 6) |
| Retrieved chunks (bottom 6 of 12) | 4,800 | 3 — ranked, tail truncated first | No — dropped |
| **Total included** | **7,650** | | **within 8,000** |

Fixed overhead (instructions, reserved output, current question) is 1,350 tokens, non-negotiable. History at 1,500 tokens is next in line and fits without needing compression this turn. That leaves 5,150 tokens for retrieved content — enough for roughly 6 chunks at ~800 tokens each, not all 12 the retrieval step returned. The policy's job is exactly this arithmetic, run automatically on every call rather than reasoned about by hand.

## Core Concept 4 — Context Compression

Compression is the middle-priority tool between "keep in full" and "drop entirely": summarizing older conversation turns or verbose tool output into a shorter form that preserves the gist while trading detail for space. This is a context-*engineering* decision — which content gets compressed, when, and how aggressively — distinct from [context-window's](../context-window/README.md) coverage of the token-budget mechanics that make compression necessary in the first place.

Two patterns:

- **Rolling summarization of conversation history.** Once history exceeds a turn-count or token threshold, the oldest turns are replaced with a single summary turn ("User previously asked about X and Y; assistant explained Z"), generated by a separate, cheaper model call, and the summary — not the original turns — is what gets included going forward.
- **Compressing verbose tool output.** A tool call that returns a large JSON payload (a database query returning 200 rows, a search API returning 50 results) rarely needs every field or every row in context — extracting the fields the task actually needs, or summarizing the result set ("143 of 200 rows matched criteria X; here are the top 5 by relevance"), keeps the signal without the raw bulk.

Compression is not free: it's a lossy operation performed by another model call, which means it can itself introduce errors (a bad summary can drop the one detail the current question needs) and adds latency and cost of its own. The middle-level judgment call is *when* compression earns its cost — routinely summarizing conversation history past a fixed turn count is usually worth it; compressing every single tool result regardless of size usually isn't.

## Core Concept 5 — Worked Scenario: 12 Chunks Retrieved, Budget for 6

A RAG-backed internal Q&A system receives a user question. Its retrieval step returns 12 candidate chunks, each carrying a relevance score from the vector search. The system prompt and the last 4 conversation turns are already committed to the context (Core Concept 3's table). The assembly pipeline's actual decision sequence:

1. **Compute remaining budget for retrieved content**: 8,000 total − 1,350 fixed overhead − 1,500 history = 5,150 tokens available.
2. **Sort the 12 chunks by relevance score, descending.**
3. **Walk down the sorted list, accumulating tokens, until the next chunk would exceed the remaining budget.** At ~800 tokens per chunk, that's 6 chunks (4,800 tokens), with chunk 7 (would bring the running total to 5,600, over the 5,150 remaining) excluded.
4. **Assemble the final context**: instructions, history, the top 6 ranked chunks (each still individually delimited — Core Concept 3 in [junior.md](junior.md)), then the current question.

The naive alternative — "the retrieval step already ranked them, just include everything it returned" — either blows the token budget outright (12 chunks at ~800 tokens is 9,600 tokens, over budget before instructions or history are even counted) or, if the developer truncates crudely by just cutting the raw concatenated text at the token limit, can sever a chunk mid-sentence and can just as easily cut off the *user's own question* if it happens to land at the end of an oversized blob. Ranking first and truncating by whole units (whole chunks, not raw character counts) avoids both failures.

## Core Concept 6 — Verification at Two Levels

**Unit level — the ranking and truncation logic itself:**

Feed the assembly function a fixed set of chunks with known relevance scores and a fixed budget, and assert on the output:

```python
chunks = [
    {"text": "...", "score": 0.91, "tokens": 780},
    {"text": "...", "score": 0.34, "tokens": 810},  # low relevance
    {"text": "...", "score": 0.88, "tokens": 795},
    # ... 9 more, scores ranging 0.20-0.90
]
result = assemble_context(chunks, budget_tokens=5150)

assert result.included_scores == sorted(result.included_scores, reverse=True)
assert all(c["score"] >= 0.7 for c in result.included)  # if a threshold is in play
assert sum(c["tokens"] for c in result.included) <= 5150
assert 0.34 not in [c["score"] for c in result.included]  # low-relevance chunk excluded
```

This test would fail immediately if a code change accidentally reverted to first-N inclusion instead of ranked inclusion — the low-score chunk is deliberately placed early in the input list so a first-N bug would let it slip in.

**Integrated-flow level — against a real question:**

Ask a question whose correct answer depends specifically on a chunk that ranks, say, 4th out of 12 by relevance (not 1st) — and confirm the final answer is still correct. This catches a subtler bug than the unit test: a ranking function that's mathematically correct but scores the *wrong* chunk highest (a relevance-scoring bug, not a truncation bug) would still pass the unit test above while producing a wrong answer here.

## Real-World Examples

- **A "the model got worse" complaint was a truncation-order bug.** A team's RAG assistant started giving vaguer answers after a schema change added conversation history to every call. The retrieved-chunk budget shrank accordingly, but the truncation logic still cut by raw character count across the whole concatenated blob rather than by whole ranked chunks — occasionally cutting the single most relevant chunk off mid-sentence while a lower-relevance chunk survived intact earlier in the blob. Switching to rank-then-truncate-by-whole-chunk fixed it without changing the retrieval step at all.
- **Compression saved a support bot from repeating itself.** A long-running support chat kept resending the full history every turn; past a certain length, the model started re-asking questions the user had already answered because the relevant detail was buried dozens of turns back, diluted by everything after it. Rolling summarization of turns older than the last 6 kept the key facts ("user's order number is X, issue is a damaged item") present in a compact form instead of losing them in an ever-growing, undifferentiated history block.

## Common Mistakes

- **Including every retrieved chunk regardless of score, relying on the token limit to eventually error out.** Fails late, fails hard (an API error mid-session), and wastes budget on low-relevance content long before the hard limit is even hit.
- **Truncating by raw character or token count across the whole concatenated context instead of by whole ranked units.** Can sever a chunk mid-sentence, or worse, truncate the user's own question if it happens to land near the cut point.
- **Treating "first N chunks the retrieval step returned" as equivalent to "top N by relevance."** Only true if the retrieval step itself sorts by relevance and nothing reorders the list afterward — an easy assumption to silently break.
- **Compressing conversation history on every single turn regardless of length.** Adds unnecessary latency and cost, and risks losing recent detail that didn't need compressing yet.
- **Never testing what survives truncation under budget pressure**, only testing that the pipeline works when everything comfortably fits — the failure mode that matters is specifically the one under pressure.

---

## Apply it

1. Take (or build) a small RAG pipeline that retrieves at least 8-10 chunks for a query, each with a relevance score.
2. Implement a priority policy matching Core Concept 3: system instructions and current question never dropped, recent history compressed before being dropped, retrieved chunks ranked and truncated from the tail.
3. Pick a token budget deliberately smaller than what all retrieved chunks plus history would need, and run the pipeline — confirm the assembled output includes the highest-scoring chunks, not the first N returned by retrieval.
4. Write the unit test from Core Concept 6: assert the included chunks are sorted by score and the excluded ones are the lowest-scoring, using a fixed input where you know the expected outcome in advance.
5. Add a rolling-summarization step for conversation history past a turn-count threshold you choose, and confirm a long conversation's assembled context stays under budget without losing the fact the current question depends on.

## Verify your work

- Under a budget you deliberately set below what all candidate content would need, the included retrieved chunks are the highest-relevance ones, not an arbitrary or first-N subset — confirmed by a test with known scores, not by inspection alone.
- Truncation happens at whole-chunk boundaries, never mid-sentence or mid-chunk.
- System instructions and the current user question are present in 100% of your test runs, regardless of how tight the budget is.
- A long conversation history triggers compression before it triggers an outright drop of older turns, and the compressed summary still contains the fact a later question in your test depends on.
- You can state, for a specific test call, the exact token accounting (fixed overhead + history + included chunks = total), matching the format in Core Concept 3's table.

## Review questions

- Why is "the retrieval step already returns chunks in relevance order" an assumption worth verifying rather than trusting by default?
- In the priority policy from Core Concept 3, why are system instructions and the current user turn never dropped, while retrieved documents are the first candidates for truncation?
- What specifically can go wrong when truncation is implemented by cutting raw token or character count across a concatenated blob, instead of by whole ranked units?
- When is compressing conversation history worth its cost, and when is it not?
- What's the difference between a unit-level test of the ranking/truncation logic and an integrated-flow test of the same pipeline, and what failure does each catch that the other wouldn't?
