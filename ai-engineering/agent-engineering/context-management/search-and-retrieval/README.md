# Search and Retrieval

> Most retrieval problems are search problems. Reach for `grep` and ranked lexical search before reaching for an embedding.

```mermaid
flowchart LR
    J["Junior: grep and glob as default tools"] --> M["Middle: rank results with BM25"]
    M --> S["Senior: search agentically, not one-shot"]
    S --> P["Professional: run search as shared infrastructure"]
```

## Levels

| Level | Guide | You are done when |
|---|---|---|
| Junior | [Grep and glob as default tools](junior.md) | You can explain why exact/regex search is usually the right first tool, and use it to answer a real question. |
| Middle | [Rank results with BM25](middle.md) | You can compute a BM25 score by hand and explain when lexical ranking beats semantic search. |
| Senior | [Search agentically, not one-shot](senior.md) | You can design an iterative search→read→refine loop and a hybrid fusion strategy, with a token budget. |
| Professional | [Run search as shared infrastructure](professional.md) | You can operate a search index as a service with freshness SLOs, ACL enforcement, and a relevance regression suite. |

## Practice rule

Before building or calling a retrieval system, ask: does the query contain an exact term, identifier, or error code the answer must match? If yes, lexical search wins by default — don't reach for embeddings until lexical search demonstrably fails on real queries.

## Related

- [RAG and Vector Decisions](../rag-and-vector-decisions/) — when lexical search stops being enough and what to add on top of it.
- [Context Fundamentals](../context-fundamentals/) — the budget that caps how many search results can be returned.
- [Tool Interfaces and MCP](../tool-interfaces-and-mcp/) — how a search tool is exposed to the model as a callable interface.
