# Knowledge Base Design — Senior

<!-- level-focus -->
At senior level, focus on this question:

> How do you design retrieval so a user can never receive a chunk from a document they aren't authorized to access — and what do you give up (latency, recall, operational simplicity) to guarantee that, rather than merely making it likely?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core Concept 1 — Why This Is a Security Bug Class, Not a Quality Bug

A naive RAG pipeline retrieves the top-k most similar chunks globally, across the entire indexed corpus, with no regard for who's asking. The moment a knowledge base contains any document with restricted access — an HR file with individual compensation data, a legal document under privilege, a customer's private support ticket in a multi-tenant product — this becomes a genuine access-control vulnerability, not a relevance problem. Unlike a bad chunking choice (which produces a worse answer) or a stale document (which produces an outdated answer), an unauthorized-access leak produces exactly the answer the pipeline is designed to produce — a correct, well-grounded, well-cited answer — sourced from content the requesting user should never have seen. It's the retrieval-and-generation loop working exactly as intended, on the wrong input, and it usually doesn't error, log unusually, or look any different from a normal successful query. That combination — no anomalous signal, and a working design being the mechanism of the breach — is why it needs to be treated with the same rigor as any other access-control vulnerability class, not folded into general RAG quality work.

## Core Concept 2 — Pre-Filtering vs Post-Filtering, and Why Only One Is Actually Safe

Two places to enforce an access-control check, with very different guarantees:

- **Post-filtering** — run similarity search across the whole corpus, get back top-k results, *then* drop any the user isn't authorized to see. This is broken in two distinct ways: first, if the user's authorized content ranks below the top-k cutoff (common when a user has access to a narrow slice of a large corpus), the post-filter can silently reduce the result set to zero usable chunks even though authorized, relevant content exists further down — the same recall-degradation mechanism described for any selective filter in [Embeddings and Vector Databases — Middle](../embeddings-and-vector-db/middle.md), except here the "degraded quality" framing understates the real severity, since the actual failure users report is "the assistant knows nothing," while the far more dangerous version of the same design is: **the unauthorized chunk's content reached application code, was compared, scored, and only discarded at the very last step** — meaning it may have already been logged, cached, or (worst case) mistakenly included if the discard step has a bug. Post-filtering makes correctness depend on every downstream code path remembering to filter correctly, every single time.
- **Pre-filtering** — encode authorization as filterable metadata on every chunk at ingestion time (an `allowed_groups` or `acl` field, following the metadata pattern from [junior.md](junior.md)), and apply it as a hard filter *inside* the vector database query itself, so unauthorized chunks are never scored, never returned to application code, and never reach the LLM's context or any log downstream of the query. This is the only approach that gives an actual guarantee rather than a best-effort behavior — the unauthorized content structurally cannot appear in the result set, because the database itself excludes it from consideration.

The decision rule is unconditional at this level: **access control for RAG retrieval must be enforced as a pre-filter inside the retrieval query, never as a post-hoc step on already-fetched results.** This isn't a preference between two reasonable options — post-filtering is the wrong design whenever any content in the corpus has differentiated access, because it makes the security guarantee dependent on every consumer of retrieved results remembering to check correctly, which is exactly the kind of distributed, easy-to-forget responsibility that access-control failures typically come from.

## Core Concept 3 — Keeping ACL Metadata in Sync With the Source of Truth

Encoding access control as ingestion-time metadata creates a new problem: **the metadata is only correct as of ingestion time**, and permissions change after that — an employee leaves a team and loses access to that team's documents, a document gets reclassified from internal to restricted, a customer's support agent role is revoked. If the knowledge base's `acl` field isn't updated when the source system's permissions change, retrieval keeps enforcing a stale, wrong policy — either over-restrictive (annoying) or under-restrictive (a real leak, and the more dangerous direction to get wrong).

The fix is to treat ACL changes exactly like the content changes covered in [middle.md](middle.md): the source system's permission changes need to be a change-detection trigger, propagated through the same event-driven-with-polling-backstop pipeline, updating the `acl` metadata field specifically — not waiting for the document's *content* to change to also refresh its *permissions*. This needs its own propagation-latency target, tracked separately from content freshness, because the cost of stale permissions (a security gap) and the cost of stale content (a quality gap) are different in kind, not just degree, and deserve different urgency.

## Core Concept 4 — Chunk-Level vs Document-Level Access Control

Document-level ACLs (this whole document is restricted to group X) are the simpler case, but real documents often have finer-grained access needs — a single contract with one clause under legal hold while the rest is generally readable, an internal wiki page with one paragraph containing a salary figure that shouldn't be broadly visible even though the rest of the page is fine for anyone. Document-level ACL metadata can't express this; it has to be attached at the **chunk** level, which means the chunking strategy chosen in [RAG Techniques — Middle](../rag-techniques/middle.md) directly determines the smallest unit of access control achievable — chunking a sensitive document too coarsely (the whole document as one chunk) forces an all-or-nothing access decision even when the underlying sensitivity is more granular, and chunking too finely can fragment context needed to correctly assess sensitivity in the first place. This is a case where a decision made in the retrieval-techniques topic for relevance reasons has a direct, non-obvious security consequence, and the two decisions can't be made independently on a document type with mixed-sensitivity content.

## Core Concept 5 — The Recall-vs-Isolation Trade-off

Pre-filtering by ACL interacts with ANN search the same way any selective metadata filter does (per [Embeddings and Vector Databases — Middle](../embeddings-and-vector-db/middle.md)): a highly restrictive filter (a user authorized for only a small slice of a large corpus) can reduce effective recall within an HNSW index, because the graph's navigable paths were built across the whole collection and a narrow, scattered authorized subset may have fewer good paths to traverse. Two mitigations, with a real trade-off between them:

- **Raise `ef_search` dynamically when the filter is known to be highly selective** — keeps a single shared index, costs query latency, and needs the retrieval layer to actually know (or estimate) filter selectivity to decide when to raise it.
- **Maintain separate indexes or namespaces per tenant/access-group** — the namespace-per-tenant pattern from [Embeddings and Vector Databases — Professional](../embeddings-and-vector-db/professional.md), which sidesteps the recall problem entirely (no filtering needed within a namespace that's already fully authorized) at the cost of more indexes to build, maintain, and keep in sync, and is the stronger isolation guarantee when access boundaries are stable and few (e.g., per-customer in a multi-tenant product) rather than fine-grained and dynamic (per-document ACLs on a shared internal wiki).

Neither mitigation is free; the choice depends on whether the organization's access boundaries look more like a small number of large, stable groups (favoring separate namespaces) or a large number of fine-grained, frequently-changing individual document permissions (favoring in-index filtering with tuned `ef_search`).

## Cross-Component Scenario: "A User Reports Seeing Content They Shouldn't"

| Hypothesis | Confirming evidence | Disconfirming evidence |
|---|---|---|
| **Post-filtering is in use, and a code path forgot to apply it** | Application logs show the unauthorized chunk was retrieved by the vector database query (present in raw search results) before any filter ran | Vector database query logs show the chunk was never returned by the database at all — filtering happened inside the query, not after |
| **ACL metadata is stale** — the user's access was revoked, but the chunk's `acl` field wasn't updated to reflect it | The document's ACL in the source system was changed more recently than the chunk's metadata `updated_at`/ACL-sync timestamp | ACL metadata sync timestamp is more recent than the source system's permission change |
| **Chunking is too coarse for the document's actual sensitivity** — a restricted paragraph was chunked together with generally-readable content, and the whole chunk inherited the more permissive ACL | The leaked content and clearly-authorized content are in the same chunk_id | The leaked content is in its own distinct chunk with its own ACL, separate from authorized content |

Checking whether the vector database's own query logs show the unauthorized chunk being returned at all is the fastest way to distinguish the first hypothesis from the other two — if the database itself never returned it, the leak is not a filtering-discipline problem, and investigation should move directly to ACL sync freshness or chunking granularity instead.

## Verification: A Red-Team Test, Not a Single Manual Check

Confirming access-control-aware retrieval works requires adversarial testing, not a one-off manual query:

1. Construct at least one test user per distinct access level in the system (unauthenticated, standard employee, a specific restricted group, an admin).
2. For a representative sample of queries known to have relevant content behind at least one access boundary, run the same query as each test user and confirm the result set differs exactly as expected — no restricted content reaches an unauthorized test user, and authorized content is not incorrectly withheld either (the over-restrictive failure is a real cost too, just a different one).
3. Repeat this after a deliberate ACL change (revoke a test user's access to a specific document) and confirm the change propagates within the target latency from Core Concept 3, not just eventually.
4. Run this as a scheduled, repeatable suite, not a single manual verification at launch — the same "audit, not one-time check" discipline the professional-level guide applies at the org-wide level.

A single successful manual query proves the design works for the case tested; it proves nothing about the query patterns, document types, or access levels not covered by that one test.

## Common Mistakes

- **Implementing post-filtering and believing it's equivalent to pre-filtering because "the result looks the same."** The result looks the same only in the successful case; the failure mode (a forgotten filter step, or content reaching a log before being discarded) is categorically worse than a pre-filter's failure mode.
- **Treating ACL sync as part of the general content-freshness pipeline with the same latency target.** Stale permissions are a security gap, not a quality gap, and often need a tighter propagation SLA than content freshness does.
- **Choosing a chunking strategy for relevance reasons alone on a document with mixed-sensitivity content.** A chunk boundary decision made without considering access granularity can force an incorrect all-or-nothing access decision.
- **Testing access control with a single manual query instead of a systematic, repeatable test across every access level.** Passes the one case tested and gives false confidence about everything else.
- **Not testing the over-restrictive direction.** A design that leaks nothing but also incorrectly withholds a user's own authorized content has a real usability and trust cost, even though it's not a security incident.

---

## Apply it

1. Take a document set (real or realistic) with at least two distinct access levels — some content everyone can see, some restricted to a subset of users.
2. Design chunk-level ACL metadata for it, deciding at what granularity (document-level or chunk-level) each document's access boundary needs to be expressed, per Core Concept 4.
3. Implement retrieval so the ACL is applied as a pre-filter inside the vector database query, and confirm — by inspecting the raw query results, not just the final application output — that unauthorized chunks are never returned by the database at all.
4. Build the red-team test suite from the Verification section: multiple test users, a representative query sample, checked against expected authorized results for each.
5. Make a deliberate ACL change (revoke one test user's access to one document) and measure how long it takes to propagate into retrieval results.

## Verify your work

- You can point to the vector database query log (not just application-level output) and confirm an unauthorized chunk was never returned, not merely filtered afterward.
- Your red-team suite covers every distinct access level in your test scenario, not just one authorized and one unauthorized case.
- You measured actual ACL-change propagation latency, not an assumed one.
- You can state, for at least one document in your test set, why you chose document-level or chunk-level ACL granularity for it specifically.

## Review questions

- Why is post-filtering not an acceptable design for access-control-aware retrieval, even when it appears to produce the same visible result as pre-filtering in the successful case?
- Why does ACL metadata staleness deserve a different (typically tighter) propagation target than general content freshness?
- How does a chunking-strategy decision made for relevance reasons alone create a security consequence on a document with mixed-sensitivity content?
- Why is a single manual test of access control insufficient evidence that the design is correct?
