# Agent Memory - Professional

Agent memory is a derived-data platform: mutable source records, indexes,
caches, compaction, consistency, retention, and deletion all influence what
the reader observes.

## Real-system mechanics

**PostgreSQL with pgvector** combines relational filters and vector indexes.
HNSW offers strong query performance but consumes more memory and has slower
builds; IVFFlat requires training and enough probes for recall. Tenant and
visibility predicates must remain effective in the chosen query plan.

**Redis** is useful for bounded recent context and TTL-based task state, but
eviction is not a durable retention policy. Replication lag and failover can
resurface older values unless the application defines version semantics.

**LangGraph checkpointing** persists graph state by thread and checkpoint,
supporting replay and interruption. Checkpoints are execution state, not
automatically curated semantic memory; conflating them causes unbounded growth
and accidental replay of stale instructions.

**Letta/MemGPT** popularized tiered memory inspired by virtual memory: a small
in-context working set and external archival storage. The analogy is useful,
but retrieval is semantic and lossy rather than address-exact like paging.

## Scale and consistency

At 10x, embedding writes and index updates lag behind source records, creating
read-after-write gaps. At 100x, HNSW memory, compaction, tombstones, and
re-embedding migrations dominate operations. Keep canonical records separate
from replaceable derived vectors so indexes can be rebuilt.

Use monotonic record versions and idempotent event consumers. A deletion must
write a durable tombstone before asynchronously removing vectors, caches, and
exports; readers must filter tombstoned IDs during the gap. Backups require a
documented expiry or deletion-replay strategy.

## Operations

Dashboard write acceptance/rejection, extraction latency, index lag, retrieval
latency and recall, filter selectivity, stale/tombstoned hits, contradiction
rate, context bytes, and deletion completion age. Sample retrieval traces with
record IDs and scores while redacting private content.

In a postmortem, avoid "the retriever returned bad memory." Identify whether
the defect entered at extraction, canonical storage, indexing, filtering,
ranking, context assembly, or model use.

## Design and operations checklist

- [ ] Canonical records are independent from rebuildable embeddings/indexes.
- [ ] Every record has tenant, provenance, version, timestamps, and retention metadata.
- [ ] Authorization filters cannot be bypassed by approximate search.
- [ ] Deletion covers replicas, indexes, caches, exports, and backup policy.
- [ ] Contradictions and corrections are modeled rather than overwritten silently.
- [ ] Index migrations have recall comparison, shadowing, and rollback.

## Cheat sheet

```text
working memory = bounded context for the current execution
episodic memory= timestamped events with provenance
semantic memory= consolidated facts/preferences
canonical store= authority; vectors are derived indexes
forgetting      = product policy plus verifiable distributed deletion
```

## Test yourself

1. How do you preserve deletion semantics while a vector index updates asynchronously?
2. Compare HNSW and IVFFlat for 100 million tenant-scoped memories.
3. Design a zero-downtime re-embedding migration with measurable recall.

## Further reading

- Packer et al., "MemGPT: Towards LLMs as Operating Systems"
- Malkov and Yashunin, "Efficient and Robust Approximate Nearest Neighbor Search Using HNSW"
- pgvector source and index documentation
- LangGraph persistence and checkpointing documentation
- Lewis et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks"
