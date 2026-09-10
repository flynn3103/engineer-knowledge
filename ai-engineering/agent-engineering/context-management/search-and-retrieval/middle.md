# Search and Retrieval — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Can you compute a BM25 relevance score by hand for a small example, and explain in concrete terms when ranked lexical search beats semantic (embedding) search?

---

## From exact match to ranked match

Grep answers "does this term appear" — it doesn't answer "which of these 40 matching documents is *most* relevant." **BM25** (Best Match 25) is the standard ranking function that scores a document against a query using term frequency and document length, without any embedding model.

BM25's score for one query term `t` in document `d`:

```
score(t, d) = IDF(t) × ( f(t,d) × (k1 + 1) ) / ( f(t,d) + k1 × (1 - b + b × |d|/avgdl) )
```

- `f(t,d)` — how many times term `t` appears in document `d`.
- `IDF(t)` — inverse document frequency: rare terms across the whole corpus score higher than common ones ("GMV" scores higher than "the").
- `k1` (commonly ~1.2–2.0) — controls **term-frequency saturation**: the 10th occurrence of a word barely adds more score than the 5th did. Without this, a document that just repeats the query word 50 times would win, which isn't actually more relevant.
- `b` (commonly ~0.75) — controls **length normalization**: a long document naturally contains more words, so its raw term count is discounted relative to its length, preventing long documents from winning purely by being long.
- A document's total score is the sum of `score(t, d)` over every query term.

## Work one example by hand

Corpus: 3 short docs about a `sales` dataset. Query: `"GMV drop Singapore"`.

| Doc | Text | Length (words) |
|---|---|---|
| A | "GMV dropped sharply in Singapore last week due to a pricing bug." | 11 |
| B | "Singapore revenue metrics dashboard overview and definitions." | 8 |
| C | "GMV GMV GMV GMV GMV Singapore Singapore Singapore." | 8 |

- Doc A: contains all three query terms once each, at typical length → solid, balanced score.
- Doc B: contains "Singapore" but not "GMV" or "drop" → low score, missing terms dominate.
- Doc C: repeats "GMV" and "Singapore" heavily but is short and nonsensical → term-frequency saturation (`k1`) keeps this from dominating Doc A despite the raw repeat count, and IDF still credits it for the rare terms present. This is the concrete case that shows saturation matters — without it, spammy repetition would win.

Rank these three by expected relevance before computing anything, then check that BM25's design (saturation + length norm) matches your intuition that A is most relevant, not C.

## When BM25 beats embeddings

- **Exact identifiers and rare terms**: an order ID, an error code, an internal acronym — BM25's IDF rewards rare exact terms; an embedding model may have never seen the term and represents it poorly.
- **Jargon and internal vocabulary**: domain-specific terms not well represented in a general-purpose embedding model's training data.
- **Cost and latency**: BM25 needs an inverted index (fast to build, no GPU), no embedding model call, no vector database.
- **Explainability**: a BM25 match can be shown as "these exact words matched" — useful when a human needs to audit why a result was returned.

## When BM25 falls short

- Paraphrase: "revenue decline" vs. a document that says "GMV drop" — zero term overlap, BM25 finds nothing even though the document is the answer. This is the case for adding embeddings or reranking on top (see [RAG and Vector Decisions](../../rag-and-vector-decisions/)).

## Hybrid as the default, not vectors alone

In production, combining BM25 with vector search (hybrid retrieval) — via a fusion method like Reciprocal Rank Fusion (RRF) — consistently outperforms either alone, because they catch different failure modes: BM25 catches exact/rare terms, embeddings catch paraphrase. Treat "pure vector search" as a special case you fall back to, not the default architecture.

## Comprehension check

- In the BM25 formula, what does `k1` control, and what breaks without it?
- In the BM25 formula, what does `b` control, and what breaks without it?
- Using the three-document example, explain in one sentence why Doc C doesn't outscore Doc A despite repeating query terms more.
- Give one query where BM25 alone fails and name the technique that would catch it.
