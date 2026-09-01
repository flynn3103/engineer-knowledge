# Embeddings and Vector Databases - Professional

Vector retrieval is a derived-index system whose correctness depends on ANN
algorithms, metadata execution, source consistency, compaction, and measurable
recall under the production workload.

## Real-system internals

**FAISS** implements exact and approximate indexes including IVF, product
quantization (PQ), and graph-based variants. IVF searches selected coarse
clusters (`nprobe` controls work/recall); PQ compresses vectors into short
codes, reducing memory at the cost of distance error.

**HNSW** builds a multilayer proximity graph. `M` affects graph degree and
memory/build cost; `efConstruction` affects build quality; `efSearch` trades
query work for recall. Deletes and heavy updates require system-specific
tombstone and rebuild behavior.

**pgvector** integrates exact, HNSW, and IVFFlat search with PostgreSQL
transactions and metadata. Query planning, filter selectivity, iterative scans,
vacuum, WAL, and replica lag influence observed results; an index benchmark
without realistic SQL predicates is incomplete.

**Qdrant** uses segment-based storage, payload indexes, HNSW, and background
optimization. Segment count, payload filter indexes, optimizer thresholds, and
replication consistency affect latency during ingestion and compaction.

## Scale and failure behavior

Raw float32 storage is `count x dimensions x 4` bytes before graph, IDs,
metadata, replicas, and allocator overhead. At 100 million 1536-dimensional
vectors, raw vectors alone are about 614 GB. HNSW graph memory and replicas can
make full in-memory deployment much larger; quantization, sharding, or disk
tiers become architectural decisions.

At 10x ingestion, embedding API throughput and index compaction often fail
before query serving. At 100x, shard imbalance, graph rebuilds, filtered recall,
and replication traffic dominate. Isolate backfills, rate-limit writers, and
reserve query capacity. Use deterministic shard routing and rebalance plans.

## Consistency and operations

Canonical source changes should emit versioned idempotent events. Upsert the
new vector and durable version; deletion writes a tombstone before asynchronous
index/cache cleanup. Readers reject stale/tombstoned versions during lag.
Reconciliation compares source versions, index records, and deletion ledgers.

Dashboard query p50/p95/p99, recall probes, candidate counts before/after
filters, zero-result rate, index/model version, ingestion and compaction lag,
tombstones, memory/disk, shard skew, replication lag, and embedding failures.

## Design and operations checklist

- [ ] Canonical sources and transformations can rebuild every vector.
- [ ] Model, tokenizer, normalization, dimensions, and metric are versioned.
- [ ] ANN recall is tested with real filters and workload distributions.
- [ ] Capacity includes graph/PQ structures, metadata, allocator overhead, and replicas.
- [ ] Updates/deletes have durable versions, tombstones, and reconciliation.
- [ ] Backfills and compaction cannot starve online queries.
- [ ] Migrations support shadow reads, canaries, rollback, and old-index retirement.

## Cheat sheet

```text
exact kNN = full comparison, maximum recall, linear work
IVF       = search selected coarse clusters; nprobe trades speed/recall
PQ        = compressed vector codes; memory savings with distance error
HNSW      = proximity graph; fast search with memory/build trade-offs
vector index = derived artifact; canonical source remains authority
```

## Test yourself

1. Estimate total memory beyond raw vectors for a replicated HNSW deployment.
2. How would you benchmark filtered recall for one small tenant on shared shards?
3. Design reconciliation after an embedding consumer was offline for six hours.

## Further reading

- Johnson, Douze, and Jegou, "Billion-scale similarity search with GPUs"
- Malkov and Yashunin, "Efficient and Robust Approximate Nearest Neighbor Search Using HNSW"
- Jegou, Douze, and Schmid, "Product Quantization for Nearest Neighbor Search"
- FAISS, pgvector, and Qdrant source and index documentation
- BEIR benchmark and papers on hybrid information retrieval
