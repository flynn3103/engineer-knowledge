# RAG and Vector Decisions — Professional

<!-- level-focus -->
At professional level, focus on this question:

> Can you decide, at an org level, when a RAG pipeline is the right investment vs. build-vs-buy for vector infrastructure — and know when to retire one in favor of simpler lexical search or SQL?

---

## Own vs. buy for vector infrastructure

| Factor | Favors managed vector DB (Pinecone, Weaviate, etc.) | Favors self-hosted / build |
|---|---|---|
| Corpus size and query volume | Small-to-medium, unpredictable growth | Very large scale where per-query cost of a managed service dominates spend |
| Team's existing infra | No existing search/DB ops expertise in-house | Already operating Elasticsearch/OpenSearch or a Postgres+pgvector setup with spare capacity |
| Compliance/data residency | Managed provider meets requirements | Data must never leave a specific environment |
| Time to first working version | Need it running in days | Have the runway to build and are optimizing steady-state cost |

This is a genuine build-vs-buy trade-off, not a default — the professional-level responsibility is documenting which factors drove the choice, so it can be revisited when the org's scale or constraints change, rather than being permanent by inertia.

## When to retire a RAG pipeline

A RAG pipeline that was the right call at launch can become the wrong call later. Retire or scale it back when:

- The eval-set recall/precision (see senior level) has been flat or declining for months despite tuning — a sign the corpus has outgrown what the current chunking/embedding approach can serve well, and a rebuild (not a retune) is due.
- Usage data shows most queries hitting the corpus are actually structured/aggregatable and would be better served by SQL against a warehouse — the corpus was RAG'd because "make it searchable" was the reflex, not because the queries needed semantic search.
- A simpler hybrid lexical system, measured against the same eval set, performs comparably at a fraction of the infra cost — complexity that doesn't earn its cost should be removed, not maintained out of sunk-cost inertia.

## Governance of embedding model versions across teams

Once multiple teams each maintain their own RAG pipeline against a shared or overlapping corpus:

- **Standardize on one embedding model version per corpus-owning team**, with a documented upgrade cadence — uncoordinated per-team upgrades mean the same document has incompatible embeddings in different indexes, and no one can tell which index is "current."
- **Require the senior-level eval methodology (recall/precision/faithfulness) as a gate before any embedding-model upgrade ships**, org-wide — an upgrade that measurably improves one team's queries and regresses another's needs to be caught before rollout, not after a complaint.
- **Track embedding-model deprecation dates from providers** as an operational dependency, the same way a library's EOL date is tracked — a deprecated embedding endpoint disappearing without a planned migration is an outage, not a surprise.

## Comprehension check

- Name two factors that would push a team toward a managed vector database and two that would push toward self-hosting.
- Give one concrete signal that a RAG pipeline should be retired or rebuilt rather than retuned.
- Why is uncoordinated per-team embedding-model upgrading a governance risk, even if each individual upgrade is well-tested?
- What should be required before an embedding-model upgrade ships across multiple teams sharing a corpus?
