# RAG

> Ground a language model in your own data — retrieve the right evidence, hand it to the model in a form it will actually use, and prove the answer is supported by what was retrieved.

Retrieval-Augmented Generation (RAG) is the discipline of answering a question with a model that did not see your documents during training. It works by retrieving relevant material at query time and placing it in the model's context so the answer is grounded in something checkable instead of the model's parametric memory alone. Getting a demo working takes an afternoon; getting recall, precision, and faithfulness to hold up in production takes real engineering.

```mermaid
flowchart LR
    Junior["Junior: build the loop"] --> Middle["Middle: choose the strategy"]
    Middle --> Senior["Senior: diagnose the regression"]
    Senior --> Professional["Professional: run it as a platform"]
```

## Topics

| # | Topic | What you'll learn |
|---|-------|-------------------|
| 01 | [RAG Techniques](rag-techniques/junior.md) | The retrieve → augment → generate loop, chunking, hybrid search, re-ranking, and diagnosing quality regressions with evidence. |
| 02 | [Embeddings and Vector Databases](embeddings-and-vector-db/junior.md) | What embeddings represent, choosing a similarity metric and a vector database, ANN indexing trade-offs, and migrating embedding models without downtime. |
| 03 | [Knowledge Base Design](knowledge-base-design/junior.md) | Structuring documents for retrieval — metadata, freshness, deduplication, access control, and org-wide ownership of knowledge quality. |

## How to use this section

Each topic has four depth levels — **junior → middle → senior → professional**. Start at your level and climb. RAG Techniques is the entry point: it's the end-to-end loop that the other two topics feed into, so read it first even if your immediate problem is "which vector database should I use." Embeddings and Vector Databases is the retrieval engine underneath that loop — the component that turns "find relevant text" into a concrete similarity search over concrete infrastructure. Knowledge Base Design is the data foundation both of the others assume is correct — a perfect retrieval algorithm over a stale, undated, unauthorized-access-leaking knowledge base still produces a bad or unsafe answer. Read them in this order the first time through; once you're diagnosing a specific production problem, jump straight to the topic that owns it.

## Practice rule

Before changing a chunking strategy, a retrieval technique, an embedding model, or an ingestion pipeline, write down the query you expect it to fix and the metric — recall@k, faithfulness, staleness — that would tell you whether it actually did. RAG quality problems are diagnosable with evidence; don't guess at which stage of the loop is broken.

---

*Part of [Engineer Knowledge](../../README.md) → [AI Engineering](../README.md).*
