# RAG Techniques — Senior

<!-- level-focus -->
At senior level, focus on this question:

> A production RAG system's answer quality has measurably regressed. Can you determine — with evidence, not by re-tuning the prompt and hoping — whether the fault is in retrieval, augmentation, or generation, and fix the actual cause?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core Concept 1 — A Failure Taxonomy, Not a Single "RAG Is Broken"

"The RAG system gave a wrong answer" is not a diagnosis; it's a symptom with at least four distinct possible causes, each requiring a different fix:

| Failure | What happened | Where to look |
|---|---|---|
| **Retrieval failure** | The chunk containing the answer was never in the top-k results at all | Chunking, embedding model, index, query wording |
| **Rerank failure** | The right chunk was retrieved into the candidate set but scored too low to survive re-ranking into the final top-k | Reranker model, candidate set size (N in retrieve-N-then-rerank-to-k) |
| **Augmentation failure** | The right chunk reached the prompt but was truncated, buried, or crowded out before generation | Prompt template, context window budget, chunk ordering |
| **Generation failure** | The right chunk was fully present in the prompt the model saw, and the model still didn't use it | Prompt instructions, model choice, conflicting or excessive context |

The single most valuable senior-level habit is refusing to guess which of these four it is. Each is measurable independently, and conflating them wastes cycles — re-tuning a prompt template fixes nothing if the actual chunk was never retrieved in the first place.

## Core Concept 2 — Isolating the Failure With a Diagnostic Eval

The method: maintain a labeled eval set (query → the specific chunk ID(s) that should support the answer → the expected answer), and measure each stage independently rather than only the end-to-end answer:

```python
for query, expected_chunk_ids, expected_answer in eval_set:
    retrieved = retriever.search(query, top_k=5)
    retrieval_hit = any(c.id in expected_chunk_ids for c in retrieved)

    prompt = build_prompt(retrieved, query)
    augmentation_hit = all(
        chunk_text_present_verbatim(c, prompt) for c in retrieved
        if c.id in expected_chunk_ids
    )  # did the expected chunk survive prompt construction intact?

    answer = llm.generate(prompt)
    generation_hit = is_correct(answer, expected_answer)
```

This produces three numbers instead of one — retrieval hit rate, augmentation survival rate given a hit, and generation correctness given both hits. A regression that drops end-to-end accuracy from 85% to 60% while retrieval hit rate is unchanged is not a retrieval problem, full stop — continuing to investigate the vector database or the chunking strategy at that point is investigating the wrong system.

## Core Concept 3 — Scenario: Recall Dropped After a Chunking Change

**Symptom**: end-to-end accuracy on the eval set drops from 85% to 68% the week after a chunking-strategy change ships (fixed-size 500 tokens → semantic chunking).

**Diagnostic step**: run the isolated retrieval hit-rate measurement from Core Concept 2 before investigating anything downstream.

| Hypothesis | Confirming evidence | Disconfirming evidence |
|---|---|---|
| Semantic chunking's boundary detection produced worse chunks for this corpus | Retrieval hit rate itself dropped (e.g., 88% → 65%); manual inspection shows chunks that no longer contain complete facts | Retrieval hit rate unchanged; chunks inspected look at least as coherent as before |
| The embedding index wasn't rebuilt — old chunk embeddings are still being searched against a new chunking scheme's chunk IDs | `vector_store.count()` doesn't match the new chunk count; a chunk ID returned by search doesn't exist in the new chunk-to-text mapping | Index count matches; every returned chunk ID resolves to real, current chunk text |
| A reranker trained/tuned against the old chunk size distribution now scores the new (differently-sized) chunks poorly | Retrieval-before-rerank hit rate is fine; hit rate *after* reranking is what dropped | Hit rate is already low before reranking runs at all |

Pulling the retrieval hit rate first and finding it dropped from 88% to 65% ends the ambiguity immediately — the fault is upstream of generation, in the chunking change itself, most likely because semantic chunking's similarity-drop boundary detection (see [middle.md](middle.md) Core Concept 1) produced smaller, more topically-narrow chunks that no longer contained the full fact needed to answer multi-part questions. The fix is not a prompt change; it's revisiting the chunk-size floor for semantic chunking or falling back to structure-aware chunking for this specific corpus.

## Core Concept 4 — Scenario: Generation Ignores Retrieved Context

**Symptom**: retrieval hit rate is unchanged and healthy (90%+), but end-to-end accuracy has dropped. The right chunk is verifiably present in the prompt (augmentation survival rate is also fine), and the model still answers incorrectly or generically.

This is a pure generation failure, and it has a small number of common root causes:

- **Context placement** — the retrieved chunks were appended *after* a long system prompt and instructions, and the model's attention to content degrades toward the middle of a long context — a well-documented behavior sometimes called the "lost in the middle" effect, where models attend more reliably to information near the start or end of a long context than to information buried in the middle. Fix: put retrieved context immediately adjacent to the question, or restructure the prompt so the most relevant chunk (post-rerank) is placed last, closest to the question.
- **Context stuffing** — top-k was increased (e.g., from 5 to 20) to "be safe," but most of the additional chunks are low-relevance noise. The model isn't ignoring the right chunk out of malice; it's weighing it against fourteen irrelevant ones. Fix: tighten k, or add a reranker (Core Concept 5) so quantity doesn't substitute for precision.
- **Missing or weak grounding instruction** — the prompt template changed (a rewrite, a new team member's edit) and silently dropped the "answer only from the provided context" instruction from [junior.md](junior.md) Core Concept 3. Fix: restore the instruction; treat prompt templates as reviewed, tested artifacts (see [Prompt Engineering](../../llm-fundamentals/prompt-engineering/)), not free text anyone can edit ad hoc.
- **Conflicting chunks** — two retrieved chunks disagree (an outdated policy doc and its replacement, both still indexed) and the model picks the wrong one or hedges unhelpfully. This is a knowledge-base problem wearing a generation-failure costume — see [Knowledge Base Design](../knowledge-base-design/senior.md) for deduplication and versioning.

## Core Concept 5 — Techniques That Fix Genuine Retrieval and Generation Gaps

Once the failure is correctly isolated, these are the standard tools for each:

- **Query rewriting / expansion** — the user's literal query wording often doesn't match the document's wording (a support query "how do I cancel" vs. a policy doc's "terminate your subscription"). Rewriting the query with the LLM itself before embedding it — expanding it, or generating multiple phrasings and retrieving for each — recovers hits that a literal query embedding misses.
- **HyDE (Hypothetical Document Embeddings)** — instead of embedding the user's question directly, ask the LLM to generate a hypothetical *answer* to the question first, then embed that hypothetical answer and search with it. A hypothetical answer's phrasing tends to resemble the actual source document's phrasing far more than the original question does, which improves retrieval for exactly the paraphrase-mismatch cases query rewriting also targets, at the cost of one extra LLM call before retrieval even starts.
- **Cross-encoder re-ranking** — dense retrieval scores a query and a chunk independently (each gets its own embedding, compared by cosine similarity), which is fast but coarse. A **cross-encoder** reranker (e.g., a `bge-reranker` model, or a hosted reranking API such as Cohere's rerank endpoint) scores the query and chunk *together* in a single forward pass, producing a much more precise relevance score at the cost of being too slow to run over an entire corpus — the standard pattern is retrieve a larger candidate set (N=20–50) with fast dense/hybrid search, then rerank down to the final top-k (k=3–5) with the cross-encoder.
- **Multi-hop / agentic retrieval** — a question that requires combining facts from two different documents ("does the policy that superseded the one from Q1 change the reimbursement deadline?") isn't answerable by a single retrieval pass. Multi-hop retrieval issues a first retrieval, lets the model decide what it still needs, issues a second retrieval based on that gap, and repeats until it has enough to answer — this is retrieval as a tool the model calls iteratively rather than a single upfront step, and it's the RAG-specific instance of the broader agentic pattern in [AI Agent](../../ai-agent/).
- **Citation and grounding verification** — require the model to cite which chunk ID supports each claim, and verify programmatically that cited chunk IDs were actually in the retrieved set (not invented). A citation to a chunk ID that was never retrieved is a direct, checkable signal of hallucination that doesn't require a human to fact-check the prose.

## Core Concept 6 — Questions That Expose Weak Assumptions

- "If I isolate retrieval hit rate right now, on today's production traffic sample, is it actually what I assume it is — or have I only ever measured it once, at launch?"
- "Does our prompt template still contain the grounding instruction, or has it been silently edited since the eval that validated it?"
- "When we increased top-k to improve recall, did we re-measure generation accuracy, or only retrieval hit rate?" — a common trap: recall improves, but generation accuracy drops from the added noise, and the net end-to-end change goes unmeasured.
- "Can we tell, from a citation alone, whether an answer is grounded — or do we still have to manually re-read the source to check?"
- "If two chunks in our index directly contradict each other, does anything catch that before a user sees an arbitrary pick between them?"

---

## Real-World Examples

- **A chunking change looked like a generation regression until the numbers said otherwise.** A team that shipped semantic chunking assumed the drop in answer quality meant the LLM had gotten "worse" at following instructions, and spent a cycle rewriting the prompt with no effect — because the actual fault, confirmed by isolating retrieval hit rate, was upstream in chunk boundaries, not in generation at all.
- **A "smarter" top-k increase quietly made answers worse.** Raising top-k from 5 to 15 to chase a retrieval-recall complaint did recover more correct chunks into the candidate set, but end-to-end accuracy still dropped, because the extra low-relevance chunks diluted the model's attention (Core Concept 4) — adding a reranker to cut back down to a precise top-5 after a wider top-20 retrieve fixed both numbers at once.
- **A citation check caught a hallucination a human reviewer missed.** An answer read as fluent and plausible; the cited chunk ID, checked programmatically against the actual retrieved set, didn't exist in it — the model had fabricated a citation to a source it never saw, which prose-level review alone hadn't caught.

## Common Mistakes

- **Re-tuning the prompt before measuring which stage failed.** Wastes a cycle when the fault is retrieval, and can mask a retrieval regression by making generation squeeze a correct-sounding answer out of the wrong evidence.
- **Increasing top-k as a generic fix for "recall feels low" without re-measuring generation accuracy afterward.** More retrieved chunks can trade a recall gain for a precision loss that nets out worse end-to-end.
- **Trusting a citation without verifying it against the actually-retrieved chunk set.** A fluent-looking citation is not proof of grounding.
- **Treating multi-hop questions as a retrieval-tuning problem.** No amount of chunking or reranking fixes a question that structurally requires two retrieval passes over different documents.
- **Assuming a fixed eval set stays representative forever.** Production query patterns drift; an eval set built at launch and never refreshed can hide a regression on a query type that didn't exist when the set was written.

---

## Apply it

1. Take (or build) a labeled eval set of at least 20 query → expected-chunk-ID → expected-answer triples.
2. Instrument your pipeline to measure retrieval hit rate, augmentation survival rate, and generation correctness as three separate numbers, per Core Concept 2.
3. Deliberately introduce one regression — shrink chunk size aggressively, or strip the grounding instruction from the prompt — and confirm which of the three numbers moves. Confirm the other two stay stable.
4. Add a cross-encoder reranker in front of generation and measure whether it improves generation correctness on queries where retrieval hit rate was already fine but the right chunk wasn't ranked first.
5. Write the evidence table (hypothesis / confirming evidence / disconfirming evidence) you'd use to distinguish a retrieval regression from a generation regression, using your own three numbers as the evidence source.

## Verify your work

- You can state, for a given regression, which of the three stages (retrieval, augmentation, generation) moved — with a number, not an impression.
- You have at least one concrete example where isolating the stage changed which fix you applied, versus what you would have guessed first.
- A citation-verification check exists and would catch a fabricated citation, not just a plausible-sounding one.
- You can explain why increasing top-k is not a strictly-positive change without also re-measuring generation accuracy.

## Review questions

- Why is "the RAG system gave a wrong answer" not sufficient to decide what to fix?
- What three numbers would you compute to distinguish a retrieval failure from a generation failure, and what does each one isolate?
- Why can raising top-k improve retrieval hit rate while making end-to-end answer accuracy worse?
- What is the difference between query rewriting and HyDE, and why do both target the same underlying mismatch problem?
- Why is a cross-encoder reranker typically applied to a candidate set of 20–50 chunks rather than run over the whole corpus?
