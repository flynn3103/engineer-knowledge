# RAG and Vector Decisions — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Given a real retrieval need, can you use a decision framework — not instinct — to choose between "fits in the prompt," lexical search, SQL, or RAG with embeddings?

---

## The decision framework

| Situation | Right tool | Why |
|---|---|---|
| Corpus is small (~50 pages) and stable | Put it directly in the prompt / cache it | No indexing infra needed; retrieval only adds a chance of missing the right piece. |
| Query needs code, config, IDs, error codes, exact identifiers | Lexical search (grep/BM25) | Exact terms match exactly; embeddings represent rare/exact tokens poorly. |
| Query is about structured, aggregatable facts ("total GMV last week by country") | SQL against the warehouse | This is a database query, not a document-retrieval problem — see [Tool Interfaces and MCP](../../tool-interfaces-and-mcp/) for `bq`/BigQuery MCP. |
| Large prose corpus, questions paraphrased differently than the source docs | Hybrid: BM25 + embeddings + rerank | Neither lexical nor vector alone reliably wins across both exact and paraphrased queries. |
| "What changed since yesterday" | Freshness-filtered lexical/metadata search, not a stale vector index | An index that reindexes nightly cannot answer questions about today. |

For the data-analyst agent's GMV question: the *number* ("what was GMV yesterday") is a SQL query against BigQuery, not a RAG lookup — RAG is for the "why," pulling relevant runbook/policy prose once the number itself is already known.

## Chunking that respects structure

If RAG is the right call, how a document is split into chunks determines whether retrieval can even find the right piece:

- **Chunk on natural boundaries** — headings, paragraphs, function bodies — not a fixed character count that can slice a table in half or split a code function from its docstring.
- **Keep chunks self-contained** — a chunk that says "as shown above, this applies" with the "above" cut off is useless in isolation; add minimal surrounding context (e.g., the section heading) to each chunk.
- **Size for the embedding model and the budget** — very large chunks dilute the embedding (the vector represents an average of everything in it, diffusing meaning); very small chunks lose context. A few hundred tokens per chunk is a common starting point, tuned against the eval set, not fixed by convention.

## Hybrid as the default, reranking on top

As introduced in [Search and Retrieval](../../search-and-retrieval/senior.md): run BM25 and vector search together, fuse with RRF, then rerank the fused candidates with a cross-encoder before handing the final top-k to the model. Treat "just embeddings, no BM25, no rerank" as the exception you fall back to for a narrow, well-scoped corpus — not the default architecture for a general knowledge base.

## Comprehension check

- Using the decision table, which tool would you pick for "list every column in the `orders` table" and why?
- Which tool would you pick for "why does our refund policy exclude promotional orders" and why?
- Give one concrete way bad chunking (not bad retrieval logic) can cause a RAG system to miss an answer that's clearly present in the corpus.
- Why is "just embeddings, no BM25" the exception rather than the default in a production RAG system?
