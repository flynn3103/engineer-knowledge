# Embeddings and Vectors — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Can you name what vectors actually enable, choose a chunking strategy, and say when plain keyword search is the better (and cheaper) answer?

---

## What you can build

- **Semantic search**: find documents by meaning instead of exact keywords — the direct application of nearest-neighbor ranking.
- **Deduplication and near-duplicate detection**: near-identical texts land nearly on top of each other; flag pairs above a similarity threshold.
- **Classification and routing**: embed an incoming ticket, compare to labeled examples, route to the nearest category — a classifier without training a classifier.
- **Clustering**: group embedded data by proximity to discover themes you didn't pre-label.
- **RAG**: retrieve the most relevant chunks and put them in a chat model's context — the pipeline that makes a model answer from *your* data.

## Chunking — the design decision that dominates quality

- Vectors represent *chunks*, not whole documents. Where you cut determines what can be retrieved well.
- Too small: chunks lose surrounding context ("…click the button" — which page? which button?). Too large: one chunk covers many topics and drowns its own signal.
- Working defaults: split on natural boundaries (headings, paragraphs) into chunks of roughly 200–500 tokens, with 10–20% overlap between consecutive chunks.
- Store metadata with each chunk (source doc, section title) — retrieved chunks are more useful when the model knows where they came from.

## Dimensions and cost, practically

- Wider vectors (more dimensions) mean finer-grained similarity but more storage and slower comparisons — 1536-dim vectors are ~4× the storage of 384-dim.
- Embedding cost is real but small compared to chat; storage and query speed dominate at scale. Don't optimize dimension width before you have a measured problem.

## When keyword search wins

- **Exact identifiers**: error codes, SKUs, function names — users search for exact strings, and "semantically related" is actively wrong.
- **Zero-embedding-cost**: BM25/keyword search needs no models, no vector store, no re-embedding pipeline — dramatically simpler to own.
- **Strict-freshness or exact-match domains**: legal citations, part numbers, config keys.
- Hybrid (vector + keyword, merged) covers both; but start with the simplest thing that answers the actual query pattern. The full decision framework lives in [RAG and Vector Decisions](../../context-management/rag-and-vector-decisions/).

## Common Mistakes

- **Defaulting to a vector database before checking query patterns.** If queries are exact-match, vectors add cost and lose precision.
- **Uniform character-count chunking.** Splits mid-sentence, mid-thought; boundaries (headings, sections) carry meaning and should drive cuts.
- **No overlap between chunks.** Facts spanning a boundary get destroyed by the cut.
- **Storing bare chunks without metadata.** Retrieved text without provenance is harder for the model ( and humans) to use.

## Apply It

1. Take one search need in your product; classify its queries — exact-match or meaning-based — and pick keyword, vector, or hybrid with a stated reason.
2. Chunk one real document two ways (fixed chars vs. heading boundaries + overlap); run the same queries against both and compare top-3 results.
3. Add source metadata to every chunk and confirm your app surfaces it.

## Verify Your Work

- The keyword-vs-vector choice cites the actual query patterns, not fashion.
- Chunking respects natural boundaries with overlap — measured, not default.
- Every stored chunk carries metadata identifying its source.

## Review Questions

- Why does a chunk split mid-thought damage retrieval more than a slightly-too-long chunk?
- Why is a vector store the wrong first choice for a lookup-by-error-code feature?
- What do 10–20% chunk overlap and heading-boundary splits each protect against?
