# Retrieval-Augmented Generation - Professional

Production RAG is a search platform joined to a generative interface. Search
recall, ranking, consistency, provenance, and access control remain first-class
even when the final response is natural language.

## Real-system internals

**Apache Lucene/Elasticsearch** implements BM25 over inverted indexes. Segment
creation/merging, analyzers, field norms, refresh intervals, filters, and shard
routing determine lexical recall, freshness, and latency.

**FAISS/HNSW vector retrieval** supplies semantic candidates with approximate
recall trade-offs. ANN parameters must be benchmarked with real metadata
filters; oversampling after a selective ACL filter can still return too few
authorized candidates.

**ColBERT** performs late interaction between query and document token
embeddings using MaxSim. It preserves fine-grained matching better than one
vector per passage but increases index size and scoring work. It is a retrieval
architecture decision, not merely another embedding model.

**LlamaIndex, LangChain, and Haystack** provide ingestion and retrieval
abstractions. Their convenience does not define consistency, ACL semantics,
evaluation, or operational ownership; inspect generated queries, metadata
filters, retries, and version behavior.

## Multi-stage architecture

Use high-recall candidate generation, deterministic ACL filtering, fusion,
costlier reranking, diversity-aware context selection, then grounded
generation. Cache only with keys including tenant/permissions, source/index
version, query transformation, retrieval configuration, and model versions.

At 10x, parsing/embedding backfills compete with online indexing and retrieval.
At 100x, shard fan-out, reranker GPU queues, context tokens, and trace payloads
dominate cost. Isolate workload classes, cap fan-out/candidates, batch reranking,
and degrade by skipping optional expansion before dropping core retrieval.

## Consistency and operations

Maintain a canonical source catalog with owner, authority, ACL, version,
effective dates, parse status, and index checkpoints. Events are idempotent;
deletions create durable tombstones. Reconciliation compares source catalog,
lexical index, vector index, and caches rather than trusting pipeline success.

Dashboard source coverage, parse errors, index freshness/lag, recall probes,
zero-result rate, candidate/filter/rerank counts, citation support, unanswerable
accuracy, injection tests, ACL canaries, latency by stage, context tokens, and
successful-task cost. Keep evaluation traffic independent from production
capacity.

## Design and operations checklist

- [ ] Retrieval quality is measured before and separately from generation.
- [ ] Canonical source authority, version, ACL, and deletion state are preserved.
- [ ] Hybrid candidates and reranking are justified by slice-level evaluation.
- [ ] Cache keys prevent cross-tenant, stale, or configuration-mismatched reuse.
- [ ] Backfills, merges, and reranking cannot starve interactive traffic.
- [ ] Indirect injection cannot change policy or gain capabilities.
- [ ] Every claim/citation incident maps to a diagnosable pipeline stage.

## Cheat sheet

```text
BM25        = lexical term matching over an inverted index
dense ANN   = semantic candidate retrieval with approximate recall
fusion      = combine independent ranked lists
reranker    = expensive relevance scoring on a smaller candidate set
grounding   = claims supported by supplied authoritative evidence
RAG quality = source + ingest + retrieve + rank + pack + generate + verify
```

## Test yourself

1. When does ColBERT's late interaction justify its storage/scoring cost?
2. Design cache keys for ACL-sensitive RAG with daily source updates.
3. How would you preserve online query SLOs during a full re-embedding backfill?

## Further reading

- Lewis et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks"
- Khattab and Zaharia, "ColBERT: Efficient and Effective Passage Search via Contextualized Late Interaction"
- Robertson and Zaragoza, "The Probabilistic Relevance Framework: BM25 and Beyond"
- BEIR and KILT benchmark papers
- Lucene, FAISS, LlamaIndex, LangChain, and Haystack source/documentation
