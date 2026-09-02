# Embeddings and Vector Databases — Junior

<!-- level-focus -->
At junior level, focus on this question:

> Given a small set of texts, can you generate embeddings, store them, and retrieve the item most similar to a query — and explain why the result is similar in *meaning*, not just shared words?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core Concept 1 — What an Embedding Actually Represents

An **embedding** is a fixed-length list of numbers (a vector) that represents a piece of text's meaning, produced by a model trained so that texts with similar meaning produce vectors that are close together in that vector space, and texts with different meaning produce vectors that are far apart. "Close" and "far" are measured geometrically — this is what makes it possible to do "find similar meaning" with arithmetic instead of keyword matching.

Concretely: the sentences "the cat sat on the mat" and "a feline rested on the rug" share almost no words, but a good embedding model places their vectors close together, because it captures meaning, not surface tokens. Conversely, "the bank approved my loan" and "the river bank flooded" share the word "bank" but mean different things, and a good embedding model — because it considers the surrounding words, not the word in isolation — places those vectors farther apart than the word overlap alone would suggest.

Real embedding models produce vectors with hundreds to thousands of dimensions:

| Model | Dimensions | Notes |
|---|---|---|
| OpenAI `text-embedding-3-small` | 1536 (can be shortened, e.g., to 512, via built-in dimensionality reduction) | General-purpose, hosted API |
| OpenAI `text-embedding-3-large` | 3072 | Higher quality, higher cost and storage per vector |
| Cohere `embed-v3` | 1024 | General-purpose, hosted API, multilingual variants available |
| BGE / E5 (open, e.g. `bge-base-en-v1.5`, `e5-large-v2`) | 768–1024 | Self-hostable, no per-call API cost, competitive quality on many benchmarks |

More dimensions generally capture more nuance but cost more to store and search — this trade-off is explored in depth at middle level.

## Core Concept 2 — Similarity, By Hand

The most common similarity metric is **cosine similarity** — the cosine of the angle between two vectors, ranging from -1 (opposite meaning) to 1 (identical direction, i.e., very similar meaning), independent of vector length. A tiny worked example with 2-dimensional vectors (real embeddings have hundreds of dimensions; two keeps the arithmetic visible):

```
query:    [0.8, 0.6]
chunk A:  [0.9, 0.4]   (similar meaning to query)
chunk B:  [0.1, 0.99]  (different meaning)

cosine_similarity(query, A) = (0.8×0.9 + 0.6×0.4) / (|query| × |A|)
                             = (0.72 + 0.24) / (1.0 × 0.985)
                             ≈ 0.975

cosine_similarity(query, B) = (0.8×0.1 + 0.6×0.99) / (|query| × |B|)
                             = (0.08 + 0.594) / (1.0 × 0.995)
                             ≈ 0.677
```

Chunk A scores higher — it's the closer match. In practice you never compute this by hand at scale; a vector store or a library like `numpy` does it, but the arithmetic is worth doing once so "similarity score" isn't a magic number.

## Core Concept 3 — A Small, Concrete Example

Five short texts:

```python
texts = [
    "The cat sat on the mat.",
    "A dog barked at the mailman.",
    "The feline rested comfortably on the rug.",
    "Stock prices fell sharply today.",
    "The market experienced a significant decline.",
]

embeddings = [embed(t) for t in texts]  # each returns a vector, e.g. 1536 floats

query = "Where was the cat sitting?"
query_embedding = embed(query)

scores = [cosine_similarity(query_embedding, e) for e in embeddings]
ranked = sorted(zip(texts, scores), key=lambda x: x[1], reverse=True)
```

Expected result: text 1 ("The cat sat on the mat") ranks highest — direct match. Text 3 ("The feline rested comfortably on the rug") ranks second — different words, same meaning, which is the entire point of using embeddings instead of exact keyword search. Texts 4 and 5 (about stock prices) rank lowest for this query but should rank *near each other*, since they share meaning with each other even though neither matches the query.

## Core Concept 4 — Storing and Searching a Small Set

At this scale (a handful to a few thousand vectors), no dedicated vector database is required — an in-memory list and a linear scan for the nearest vector, sometimes called **brute-force** or **exact** search, is simple, always exactly correct, and fast enough:

```python
def search(query_embedding, stored_embeddings, texts, top_k=3):
    scored = [
        (texts[i], cosine_similarity(query_embedding, e))
        for i, e in enumerate(stored_embeddings)
    ]
    return sorted(scored, key=lambda x: x[1], reverse=True)[:top_k]
```

This is exact — it compares the query against every stored vector, so it always finds the true nearest neighbors, with no approximation. The moment the collection grows large enough that a linear scan becomes too slow (discussed with real numbers in [middle.md](middle.md)), the answer is an **approximate nearest neighbor (ANN)** index inside a dedicated vector database — but reaching for one before you need it, at this scale, adds infrastructure for a problem you don't have yet.

## Common Mistakes

1. **Comparing embeddings from two different models.** A vector from `text-embedding-3-small` and a vector from `bge-base-en-v1.5` are not in the same space — even if they happen to have compatible dimensionality, comparing them produces a meaningless number, not a small-but-valid similarity score. Always embed the query with the exact same model and version used to embed the stored content.
2. **Ignoring the model's token limit.** Every embedding model has a maximum input length (commonly 8,191 tokens for OpenAI's embedding models); text beyond that limit is silently truncated by many client libraries rather than rejected, so a long document embedded without chunking first may only actually represent its opening section.
3. **Expecting exact keyword-match behavior.** A search for an exact product code, an error string, or a proper noun can rank a semantically-similar-but-wrong result above the literal match, because embeddings represent meaning, not exact strings — this is the motivating problem for hybrid search, covered in [RAG Techniques — Middle](../rag-techniques/middle.md).
4. **Not normalizing when a library expects it.** Some similarity implementations assume unit-length vectors and compute a plain dot product for speed, silently giving wrong rankings if the vectors weren't normalized first; cosine similarity's own formula (Core Concept 2) already divides out vector length, so this mistake typically comes from using dot product directly and forgetting the normalization step it depends on.
5. **Treating a low similarity score as "irrelevant" without a threshold check.** A score of 0.4 might be the best match available and still be the right answer to return — or it might mean nothing in the collection is actually relevant. Whether the top result is good enough is a judgment that needs a threshold decided from real examples, not assumed from the number's magnitude alone.

## Apply it

1. Pick 8–10 short texts covering at least two unrelated topics (e.g., some about a hobby, some about a work topic).
2. Generate embeddings for all of them using one real embedding model (a hosted API or a small open model run locally).
3. Write 3 queries: one that should closely match one specific text, one that should match by meaning without matching by exact words, and one that shouldn't strongly match anything in the set.
4. Run cosine similarity search for each query against all stored embeddings, and rank the results.
5. For the paraphrase query, confirm the correct match still ranks highest even though it shares few or no words with the query.

## Verify your work

- The paraphrase query (different words, same meaning) returns the intended match as the top or near-top result, not buried below unrelated texts.
- The unrelated-topic query returns its lowest similarity scores for texts about the other topic.
- You can compute cosine similarity for at least one pair by hand (or by a one-line calculation) and confirm it matches what your search code returns.
- Re-running the query embedding through a *different* embedding model and comparing it against the same stored vectors produces visibly nonsensical rankings — confirming why matching models matters.

## Review questions

- What makes two pieces of text produce embeddings that are close together in vector space?
- Why is comparing a vector from one embedding model against a vector from a different embedding model invalid, even if the dimensions happen to match?
- What does cosine similarity measure, and why is it insensitive to vector length?
- At what point does a linear brute-force scan stop being a reasonable search strategy, and what replaces it?
