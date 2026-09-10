# Search and Retrieval — Professional

<!-- level-focus -->
At professional level, focus on this question:

> Can you operate search as shared infrastructure across an org — with freshness guarantees, access control enforced at query time, and a regression suite that catches relevance decay before users do?

---

## Search as a service, not a per-agent library

Once more than one agent needs retrieval, a shared search service (index + query API) beats every team building its own:

- **One index, many consumers** — the dbt-repo index and the docs index are built once and queried by the data-analyst agent, a support agent, and a human-facing search bar alike, instead of three separate re-indexing pipelines drifting out of sync.
- **Freshness SLO** — define and monitor "how stale can the index be" (e.g., "docs re-indexed within 15 minutes of edit"). A stale index silently returning outdated answers is worse than an empty result, because it looks confident.
- **Central ranking tuning** — `k1`/`b` (BM25) and fusion weights tuned once against a shared eval set, not re-guessed per team.

## Access control at query time, not after

The single most common production security bug in retrieval systems: an index built once across all documents, with row/document-level permissions checked only *after* retrieval (or not at all) — so a user's query can surface a document they're not authorized to see, even if the final rendered answer tries to filter it out.

- Enforce ACLs as a **filter in the query itself** (e.g., a metadata filter restricting results to documents the requesting user/agent is authorized for), not as a post-hoc check on already-fetched text that has already touched the model's context.
- Any document ingested must carry its access-control metadata at ingestion time — retrofitting ACLs onto an existing index is expensive and error-prone; require it from day one.

## Relevance regression suite

Treat search relevance like any other production system with a regression risk:

- Maintain a labelled eval set (query → known-relevant document IDs) covering both exact-match cases (favor BM25) and paraphrase cases (favor hybrid/embeddings).
- Run it on every change to the index, the ranking weights, the embedding model version, or the chunking strategy. A change that improves one query type while silently regressing another is only visible with this in place.
- Track recall@k and precision@k over time, the same way [Agent Evaluation](../../agent-evaluation/) tracks task-level correctness — this is the search-specific instance of that discipline.

## Cost and ownership

| Decision | Owner-level trade-off |
|---|---|
| Index refresh frequency | More frequent = fresher, more compute cost. Set per-corpus based on actual edit frequency, not uniformly. |
| Which corpora get BM25 vs. hybrid vs. vector-only | Cost scales with query volume × corpus size; don't build a vector index for a corpus that's small enough to fit in context outright. |
| Who can add a new corpus to the shared index | Ungoverned addition risks ACL gaps and index bloat with no owner. |

## Comprehension check

- Why does a single shared search service typically beat every team building its own retrieval pipeline?
- Why must access control be enforced as a query-time filter rather than a post-retrieval check?
- What does a relevance regression suite catch that a one-time relevance benchmark does not?
- Give one example of a corpus that shouldn't get a vector index at all, and why.
