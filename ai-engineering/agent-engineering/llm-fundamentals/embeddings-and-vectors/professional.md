# Embeddings and Vectors — Professional

<!-- level-focus -->
At professional level, focus on this question:

> Can you own a vector pipeline as a product — versioned indexes, planned migrations, cost at scale — and decide honestly when it should be retired?

---

## The pipeline as a owned system

- A vector pipeline is: embedding model + chunking rules + index + refresh process + retrieval service. Each part has a version and an owner; "the vector DB" is not the system.
- Track the system's health as metrics, not vibes: recall@k on the labeled set (see [Senior](senior.md)), index freshness lag, query p95 latency, storage growth.

## Versioning: corpus, chunker, model

- Every index is the product of three versions: which documents, which chunking rules, which embedding model. Record all three per index — a retrieval regression is un-diagnosable without knowing which one changed.
- Freeze and version chunking rules like code; a chunking change is a *full re-embedding* event, not a tweak.

## Re-embedding migrations as routine

- Model upgrades and chunking changes both demand full re-embeddings. Make the path routine: build new index in parallel → measure recall@k on the new index → cut over atomically → keep the old index for rollback.
- Budget re-embedding cost and time as a recurring line item, not a surprise — embedding-model progress makes migrations a when, not an if.

## Cost at scale

- Storage grows with corpus × dimensions; query cost grows with index size. Both are predictable — forecast them against corpus growth the way you forecast any infrastructure (see [Cost and Performance](../../agent-evaluation/cost-and-performance/)).
- Dimension width, quantized vectors, and index type (flat vs. ANN) are the levers; reach for them when a measured number demands it, not preemptively.

## When to retire the vector pipeline

- Run the honest check quarterly against the simplest alternative:
  - Would BM25/keyword search hit the same recall@k? (If queries are mostly exact-match — yes, and simpler.)
  - Would the whole corpus just fit in context with prompt caching? (Small, stable corpora — often yes.)
- If the simpler alternative matches retrieval quality, retire the pipeline: it's infrastructure you pay for forever (re-embeddings, drift, staleness) for no measured gain.

## Common Mistakes

- **No recorded versions per index.** Every quality regression becomes an archaeology project.
- **Ad-hoc re-embeddings.** No parallel-build/measure/cutover discipline means every model upgrade is a risky big-bang.
- **Paying vector-pipeline costs with no recall@k baseline.** You can't prove the pipeline earns its keep — or notice when it stops.
- **Never considering retirement.** Infrastructure adopted early often outlives its justification; the quarterly check keeps that visible.

## Apply It

1. Write down, per production index: corpus version, chunking-rules version, embedding model — and name an owner.
2. Draft the standing migration runbook: parallel index, recall@k gate, atomic cutover, rollback window.
3. Add the four health metrics (recall@k, freshness lag, p95 query latency, storage) to dashboards.
4. Run the retirement check once: compute recall@k for keyword-only on the same labeled queries, and state whether the vector pipeline still earns its cost.

## Verify Your Work

- Every production index has recorded versions and a named owner.
- Migrations follow the written runbook, with recall@k as the gate.
- The retirement check (vector vs. simplest alternative) has been run with real numbers at least once.

## Review Questions

- Why is "the vector database" an inadequate description of the system you own?
- Why is a chunking-rules change as expensive as an embedding-model change?
- What evidence justifies retiring a vector pipeline, and how often should you check?
