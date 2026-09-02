# Embeddings and Vector Databases — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Given a product's scale (vector count), latency budget, and cost constraints, how do you choose a vector database and an indexing configuration — and justify it against those numbers, not against whichever tool is trending?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core Concept 1 — Why Brute-Force Search Stops Working

The junior-level exact linear scan compares a query against every stored vector. That's O(n) per query — fine at a few thousand vectors, measurably slow in the tens of millions. A rough mental model: a linear scan over 10 million 1536-dimension vectors is tens of billions of floating-point multiplications per query — even highly optimized, that's tens to hundreds of milliseconds per query at best, and it gets linearly worse as the collection grows, with no way to trade a small amount of accuracy for a large amount of speed. **Approximate Nearest Neighbor (ANN)** indexes exist specifically to make that trade: give up the guarantee of finding the *exact* nearest vectors in exchange for finding *very likely* the nearest vectors, orders of magnitude faster.

## Core Concept 2 — The Two Dominant Indexing Algorithms

| Algorithm | How it works | Trade-off |
|---|---|---|
| **HNSW** (Hierarchical Navigable Small World) | Builds a multi-layer graph where each vector is connected to a small set of nearby vectors; search "hops" through the graph toward the query, getting closer each step | High recall (often 95%+ against exact search) at low latency; higher memory footprint because the graph structure itself must be held alongside the vectors; good default up to tens of millions of vectors on a single node |
| **IVF** (Inverted File Index), often paired with **PQ** (Product Quantization) as IVF-PQ | Clusters vectors into partitions ("cells") during a training step; search only scans the handful of partitions closest to the query instead of everything; PQ additionally compresses each vector into a small code to save memory | Lower memory footprint (PQ compression can shrink storage substantially versus raw float vectors), tunable to very large scale; typically lower recall than HNSW at comparable speed, and requires a training step on representative data before the index is usable |

The practical default: **HNSW** for most workloads up to the tens-of-millions-of-vectors range, because its recall is high out of the box and it needs no training step — you can insert and query immediately. **IVF-PQ** earns its complexity at the scale where HNSW's memory footprint becomes the actual constraint (hundreds of millions to billions of vectors), where compressing each vector is what makes the index fit in memory (or on affordable disk) at all.

Two tunable parameters matter in practice for HNSW: `ef_construction` (build-time — higher values build a more thorough graph, at slower index-build time) and `ef_search` (query-time — higher values search more of the graph per query, trading latency for recall). Raising `ef_search` is the first lever to pull when recall is measured too low; it costs latency, not a rebuild.

## Core Concept 3 — Vector Database Landscape

| Database | Model | Strengths | Trade-offs |
|---|---|---|---|
| **Pinecone** | Fully managed, serverless | No infrastructure to operate; scales without capacity planning | Cost scales directly with usage (reads/writes/storage); less control over exact indexing internals |
| **Weaviate** | Open-source, also offered managed | Built-in hybrid (dense + BM25) search; GraphQL and REST APIs; modular embedding-model integration | Self-hosting requires real operational investment (cluster sizing, upgrades) |
| **Qdrant** | Open-source, also offered managed | Strong filtering performance, written in Rust for low resource overhead, straightforward HNSW tuning | Smaller ecosystem/plugin surface than some competitors |
| **Milvus** | Open-source, built for very large scale | Designed for billions of vectors, supports IVF-PQ and other large-scale index types natively, strong horizontal scaling story | Meaningfully more operational complexity (it's a distributed system with several component services) than the others at small-to-medium scale |
| **pgvector** | Postgres extension | No new infrastructure if data already lives in Postgres; transactional consistency with the rest of your relational data; supports HNSW indexes | ANN performance and tooling maturity historically trail purpose-built vector databases at very large scale, though this gap has been narrowing |

## Core Concept 4 — A Decision Table by Scale, Latency, and Cost

| Scale | Recommended default | Reasoning |
|---|---|---|
| Under ~100K vectors | Exact search, or pgvector without an ANN index | Brute-force is fast enough at this size; adding ANN infrastructure buys nothing yet and adds approximation error for no benefit |
| ~100K – 10M vectors | Qdrant or Weaviate, HNSW | Sweet spot for HNSW's recall/latency profile; managed or lightly-operated self-hosted options both viable at this scale |
| ~10M – 100M+ vectors | Milvus, or Pinecone if avoiding self-managed infrastructure is worth the usage-based cost | Memory footprint and horizontal scaling start to matter more than ease of setup |
| Very large (100M+), cost-sensitive on memory/storage | Milvus or another IVF-PQ-capable system, tuned for compression | Raw HNSW's memory footprint becomes the binding constraint; PQ compression is what makes the index affordable to hold in memory at all |

This table is a starting point to validate, not a rule to apply blindly — the right choice for a specific product also depends on whether the data already lives in Postgres (favoring pgvector to avoid a new system), whether operational capacity exists to run a self-hosted cluster (favoring a managed option), and the actual measured latency requirement (a sub-20ms p95 target rules out some configurations that a 200ms target wouldn't).

## Core Concept 5 — Metadata Filtering and Its Interaction With ANN

Most real queries aren't pure similarity search — they're "find the most similar chunks *from documents this user can access*" or "*from the last 90 days*." This is **metadata filtering**, and it interacts with ANN indexing in a way that's easy to get wrong:

- **Post-filtering** — run the ANN search first, then discard results that fail the filter. Simple, but if the filter is highly selective (e.g., only 2% of the collection matches), the top-k ANN results can be filtered down to far fewer than k usable results, silently degrading recall without any error being raised.
- **Pre-filtering / filtered search** — apply the metadata filter *during* the graph or partition search, so the ANN algorithm only considers candidates that would pass the filter in the first place. This is the correct default for selective filters, and it's what Qdrant, Weaviate, and Pinecone's metadata filtering are designed to do — but a highly selective pre-filter on an HNSW graph can still hurt recall, because the graph's navigable connections were built across the *whole* collection, and restricting search to a small, scattered subset of that graph can leave fewer good paths to follow. The mitigation is the same lever as before: raise `ef_search` when the filter is known to be highly selective.

This exact interaction — a security-critical filter (access control) colliding with ANN recall — is the central problem covered at senior level in [Knowledge Base Design — Senior](../knowledge-base-design/senior.md); the mechanism described here is the infrastructure half of that problem.

## Core Concept 6 — Cross-Component Scenario: Sizing a Support-Ticket Search Feature

A product team is adding semantic search over support tickets: 2 million tickets today, growing roughly 500K/year, a target p95 latency under 100ms, and a requirement to filter by customer account (a highly selective filter — most queries scope to one account out of thousands).

Working through the decision table: 2M vectors today, projected to ~4M within 3 years, sits comfortably in the "100K–10M" band favoring HNSW over IVF-PQ — this scale doesn't yet justify PQ's compression complexity or accuracy trade-off. The selective account-ID filter (Core Concept 5) means pre-filtering support and `ef_search` tunability both matter, which favors Qdrant or Weaviate over a database with weaker filtering support. If the ticket data and its relational metadata already live in Postgres and the team wants to avoid operating a new system, pgvector with an HNSW index is a legitimate alternative worth benchmarking before ruling out, specifically because it avoids a second source of truth for ticket metadata that would otherwise need to be kept in sync with a separate vector database.

## Verification at Two Levels

**Unit level — index configuration:**

- Benchmark recall@k for the chosen ANN configuration against an exact brute-force baseline on a representative sample (e.g., 1,000 queries) — a recall below roughly 90-95% against exact search is a signal to raise `ef_search` or reconsider the algorithm choice, not to accept silently.
- Confirm metadata filtering is applied as pre-filtering, not post-filtering, for any selective filter in the product's actual query patterns.

**Integrated-flow level — load test:**

- Run a load test at the target query-per-second rate and confirm p95 (and p99) latency against the budget, not just average latency — averages hide the tail latency that determines whether the feature feels slow to real users.
- Re-run the recall benchmark under the filtered-query pattern specifically (not just unfiltered queries), since filtering is where recall silently degrades per Core Concept 5.

## Common Mistakes

- **Choosing a vector database by popularity or familiarity rather than the scale/latency/cost numbers.** A tool that's a great fit at 500M vectors adds unnecessary operational overhead at 200K.
- **Never benchmarking recall against an exact baseline.** Without this, a misconfigured ANN index (too-low `ef_search`, an untrained IVF index) can silently return poor results indistinguishable, without measurement, from "the embedding model just isn't very good."
- **Using post-filtering for a highly selective filter.** Silently returns fewer than top-k usable results with no error, and the failure only shows up as "search feels incomplete" reports from users, not a clear signal.
- **Sizing for today's vector count and ignoring growth.** A configuration that's fine at 2M vectors chosen without checking the 3-year growth projection can require a disruptive migration sooner than expected.

---

## Apply it

1. Take a realistic scale, latency, and cost target for a search feature you have or can define (vector count today and in 2–3 years, p95 latency budget, whether a selective metadata filter is required).
2. Walk the decision table in Core Concept 4 and pick a candidate database and index algorithm, writing down the specific numbers that justified the choice.
3. Stand up that configuration (or a close local equivalent) and benchmark recall@k against an exact brute-force baseline on a representative query sample.
4. If your scenario requires a selective metadata filter, benchmark recall specifically under that filtered query pattern and confirm pre-filtering is in effect.
5. Load-test at your target queries-per-second and record p95/p99 latency against your budget.

## Verify your work

- Your database and index choice cites the specific scale, latency, and cost numbers from your scenario, not general reputation.
- You have a recall@k number measured against an exact baseline, not assumed from the ANN algorithm's reputation.
- You can state whether your filtering is pre-filter or post-filter, and you've measured recall under the filtered case specifically.
- Your load test reports p95/p99 latency, not only an average.

## Review questions

- Why does an ANN index trade exactness for speed, and what does "recall" mean in that trade-off?
- What is the practical difference between HNSW and IVF-PQ, and at what scale does that difference start to matter?
- Why can a highly selective metadata filter silently reduce recall even when the underlying ANN search is configured correctly?
- What two levers would you pull first if a recall benchmark came back lower than expected, before switching indexing algorithms entirely?
