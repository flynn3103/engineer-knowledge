# RAG Techniques — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Given a real document type — legal contracts, chat logs, or source code — how do you choose a chunking strategy and a retrieval mode (dense, sparse, or hybrid) and justify the choice against the document's actual structure, not a default?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core Concept 1 — Chunking Strategies, Compared

A junior pipeline chunks by a fixed size because it's simple. At middle level, the chunking strategy is a design decision with real trade-offs:

| Strategy | How it works | Best fit | Failure mode |
|---|---|---|---|
| **Fixed-size** | Split every N tokens (e.g., 500), with some overlap (e.g., 50 tokens) so a fact near a boundary isn't fully lost | Homogeneous prose with no strong internal structure | Splits mid-sentence or mid-fact; a table or a numbered clause gets cut in half |
| **Recursive** | Try splitting on paragraph breaks first; if a chunk is still too large, fall back to sentence breaks, then to fixed-size, only as needed | General-purpose default for mixed prose (the most common approach in practice, e.g. LangChain's `RecursiveCharacterTextSplitter`) | Still structure-blind — it respects *punctuation* boundaries, not *semantic* ones |
| **Semantic** | Embed consecutive sentences, detect where similarity drops sharply, and cut there — chunk boundaries follow topic shifts, not a fixed token count | Long-form prose where topic boundaries don't align with paragraph breaks (transcripts, long articles) | More expensive (an embedding call per sentence during chunking); boundary detection can be noisy on short, list-heavy text |
| **Document-structure-aware** | Cut along the document's own structure: markdown headers, HTML tags, contract clause numbers, function/class boundaries in code | Any document with reliable native structure | Only as good as the structure is reliable — a contract with inconsistent numbering, or markdown with missing headers, degrades to fixed-size behavior |

None of these is universally correct — the right choice depends on whether the *document* has structure that carries meaning, and whether breaking that structure breaks the meaning.

## Core Concept 2 — Chunk Size Trade-offs, With Numbers

Chunk size is a dial between two failure directions:

- **Too small** (e.g., 100 tokens) — a chunk stops carrying enough context to be understood on its own. A sentence like "It must be filed within that period" is retrievable but meaningless without the preceding sentence defining "that period." This is the **lost-context-at-boundary** problem.
- **Too large** (e.g., 2000+ tokens) — a chunk mixes the relevant fact with several unrelated ones, diluting the embedding (an embedding of a long chunk is an average-ish representation of everything in it, so it matches queries about any of its topics only weakly) and wasting context-window budget on irrelevant text once retrieved.

A common working default is 300–800 tokens with 10–20% overlap, but "common default" is a starting point to measure from, not a rule — the right number is the one that maximizes retrieval hit rate (from [junior.md](junior.md) Core Concept 5) on your own eval set. Overlap exists specifically to soften the lost-context-at-boundary problem: a fact split across the end of chunk N and the start of chunk N+1 has a chance of appearing whole in the overlapping region of at least one of them.

## Core Concept 3 — Dense vs Sparse vs Hybrid Retrieval

Embedding-based (**dense**) retrieval finds semantic similarity — a query about "cancelling a subscription" can match a chunk that says "terminate your plan" even though no words overlap. It has a specific, systematic weakness: exact tokens that carry no rich semantic meaning to an embedding model — error codes, product SKUs, statute or clause numbers, function names, ticket IDs — often score poorly, because the embedding model was trained to capture meaning, not to preserve exact-string identity.

**Sparse** retrieval (classically **BM25**, a term-frequency ranking function) is the complementary tool: it scores chunks by exact and near-exact term overlap, so it reliably finds "clause 14.3(b)" or "ERR_TIMEOUT_408" when dense retrieval would rank a semantically-similar-but-wrong chunk higher.

**Hybrid search** runs both and combines the results, typically via **Reciprocal Rank Fusion (RRF)** — each chunk's final score is the sum of `1 / (rank_dense + c)` and `1 / (rank_sparse + c)` for some small constant c, so a chunk that ranks well in *either* list scores well overall, without needing the two scoring systems to share a comparable numeric scale (dense cosine scores and BM25 scores are not on the same scale, which is why naive weighted-average combination is fragile and RRF is the more common default). Real systems that support hybrid search natively include Weaviate, Qdrant, and OpenSearch/Elasticsearch (BM25 plus a dense vector field); pgvector pairs with Postgres's built-in full-text search (`tsvector`) for the sparse half.

## Core Concept 4 — Choosing a Strategy by Document Type

| Document type | Chunking | Retrieval mode | Why |
|---|---|---|---|
| **Legal contracts** | Structure-aware, by clause/section number | Hybrid, weighted toward exact match | A clause is the unit of legal meaning — splitting mid-clause changes what's enforceable-looking; queries often cite exact clause numbers or defined terms that dense-only search under-ranks |
| **Chat logs / support transcripts** | Turn- or time-window-based (e.g., a customer's message plus the agent's reply as one chunk, or a fixed window of N minutes), with speaker and timestamp as metadata, not chunk text | Mostly dense | Meaning lives in conversational flow and paraphrase, not exact terms; a customer rarely repeats the support agent's exact phrasing when asking a related question later |
| **Source code** | AST- or symbol-aware — one function or class per chunk, using a parser (e.g., tree-sitter) rather than line counts | Hybrid | A function is the smallest unit that's independently meaningful; queries frequently include an exact symbol, error message, or import name that dense-only search misses, the same failure mode as legal citations |

The decision rule this collapses to: **use structure-aware chunking whenever the document has structure that carries meaning (clauses, functions, sections); default to recursive chunking when it doesn't; add the sparse half of hybrid search whenever queries plausibly contain exact identifiers the embedding model won't represent well.**

## Core Concept 5 — Cross-Component Scenario: Migrating a Contract-Search Feature

A team ships contract search with fixed-size 500-token chunks and dense-only retrieval, because that's what the junior-level pipeline used. Two symptoms surface in the first week:

1. A query for "termination clause 8.2" returns a semantically related but wrong clause (8.4, also about termination) more often than the correct one.
2. A query about renewal terms sometimes returns a chunk that starts mid-sentence, missing the defined term ("the Initial Term") the rest of the chunk depends on.

Both symptoms trace to the original strategy choice, not a bug: symptom 1 is dense-only retrieval failing on an exact clause number (Core Concept 3); symptom 2 is fixed-size chunking cutting across a clause boundary that a structure-aware split would have respected (Core Concept 1). The fix is a strategy change, not a parameter tweak — re-chunk by clause boundary using the contract's own section numbering, and add a sparse index (BM25 over the clause text) combined via RRF with the existing dense index. Re-running the retrieval hit-rate eval from [junior.md](junior.md) before and after the change is what turns "we think this is better" into "hit rate went from 61% to 89% on the clause-number query subset" — a concrete number a team can decide to ship on.

## Under-Application and Over-Application Signals

- **Under-application**: using fixed-size chunking on a document type with strong, reliable native structure (contracts, code, structured markdown) — you're paying the lost-context-at-boundary cost for no reason when the structure was available for free.
- **Over-application**: building semantic chunking (Core Concept 1) for short, uniform documents like a FAQ or a chat transcript, where the extra embedding-per-sentence cost buys no meaningful improvement because there's no long-form topic drift to detect in the first place.
- **Over-application**: adding hybrid search to a corpus where queries never contain exact identifiers (e.g., casual internal Slack-style Q&A) — the sparse half adds infrastructure and tuning cost for a failure mode that doesn't occur in this corpus.

## Verification at Two Levels

**Unit level — chunk boundaries themselves:**

- Sample 20 chunks and manually confirm none splits a clause, function, or sentence in a way that removes a fact a human reader would consider necessary context.
- For structure-aware chunking specifically, confirm the parser actually found the structure it expected — a contract with inconsistent numbering or a code file the AST parser fails to parse should be flagged, not silently fall back to line-based chunking with no warning.

**Integrated-flow level — retrieval on the real eval set:**

- Re-run the retrieval hit-rate measurement from [junior.md](junior.md) Core Concept 5, now broken out by query type (exact-identifier queries vs. paraphrase/semantic queries) — this is what actually shows whether hybrid search helped the identifier queries without regressing the semantic ones.
- Compare hit rate before and after any chunking change on the *same* fixed eval set — changing the eval set and the chunking strategy in the same step makes the comparison meaningless.

## Common Mistakes

- **Changing chunk size and retrieval mode in the same change.** Conflates two independent variables — you can't tell which one produced the improvement (or regression) you measure.
- **Applying one chunking strategy to a corpus with mixed document types.** A knowledge base with both contracts and chat logs needs per-source-type chunking rules, not one global default.
- **Adding hybrid search without checking whether the corpus actually has exact-identifier queries.** Wasted infrastructure if the queries are all paraphrase-style.
- **Trusting semantic chunking's boundary detection without spot-checking it.** It's a similarity-drop heuristic, not a guarantee — it can produce noisy boundaries on short or list-heavy text.

---

## Apply it

1. Take a document type you have real access to (or a realistic substitute — contract templates, a support-transcript export, a code repository) and chunk it two ways: fixed-size, and the structure-aware or recursive strategy that fits its actual format.
2. Build a 15–20 question eval set split into two categories: exact-identifier queries (clause numbers, function names, ticket IDs) and paraphrase/semantic queries.
3. Run retrieval hit rate for both chunking strategies, dense-only, on both query categories.
4. Add a sparse (BM25) index and combine with RRF; re-run hit rate on both query categories and compare all four numbers (2 chunking strategies × dense-only vs. hybrid).
5. Write one sentence stating which chunking strategy and retrieval mode you'd ship for this document type, citing the specific hit-rate numbers that justify it.

## Verify your work

- You have four hit-rate numbers (not one), broken out by chunking strategy and retrieval mode, on the same fixed eval set.
- You can point to at least one specific query where hybrid search recovered a hit that dense-only retrieval missed, and explain why (an exact identifier, per Core Concept 3).
- A manual spot-check of 20 chunks shows no clause, function, or sentence split in a way that removes necessary context.
- Your written recommendation cites a number, not a preference.

## Review questions

- Why does a chunk that's too large hurt retrieval even though it contains the correct answer somewhere inside it?
- What specific weakness in dense (embedding-based) retrieval does sparse (BM25) retrieval exist to cover, and why doesn't a larger embedding model fix that weakness?
- Why is changing chunk size and retrieval mode in the same experiment a measurement mistake?
- For a document type with strong native structure, what does fixed-size chunking give up that structure-aware chunking gets for free?
