# Knowledge Base Design — Junior

<!-- level-focus -->
At junior level, focus on this question:

> Given a small, well-defined set of documents, can you design a metadata schema that makes each chunk filterable, datable, and traceable back to its source — not just readable text sitting in a vector store?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core Concept 1 — A Knowledge Base for RAG Is Not a Folder of Files

A folder of PDFs or a wiki space is browsable by a human, who brings context a machine doesn't have — they know which document is current, which team owns it, and roughly when it was written, just from clicking around. A **knowledge base for RAG** has to make all of that explicit and machine-readable, because retrieval has to find, filter, and cite the right content with no human in the loop at query time. The difference from a traditional search index (like a keyword search over a document store) is what the content is *for*: a traditional search index returns documents for a person to read and judge; a RAG knowledge base returns chunks that get fed directly into a model's context and treated as ground truth for an automatically generated answer — which raises the bar on precisely because there's no human sanity-check between retrieval and the answer reaching a user.

## Core Concept 2 — Core Metadata Fields

Every ingested chunk should carry, at minimum:

| Field | Purpose | Example |
|---|---|---|
| `document_id` | Stable identifier for the source document, independent of the chunk | `faq-2024-expense-policy` |
| `chunk_id` | Unique identifier for this specific chunk, used for citation | `faq-2024-expense-policy#chunk-3` |
| `source_uri` | Where the original document lives, so a citation can link back to it | `https://wiki.internal/expense-policy` |
| `title` | Human-readable document title, useful for display and for debugging retrieval results | `"Expense Reimbursement Policy"` |
| `created_at` / `updated_at` | When the document was written and last modified — the basis for any freshness or staleness check | `2024-01-15` / `2024-11-02` |
| `source_type` | What kind of document this is, since different types need different handling | `pdf`, `markdown`, `confluence-page`, `support-ticket` |
| `owner` | Which team or person is responsible for this content's accuracy | `finance-team` |
| `content_hash` | A hash of the raw content, used to detect whether a document has actually changed (Core Concept 3, and covered fully in [middle.md](middle.md)) | `sha256:9f2a1b...` |

Without `document_id` and `chunk_id`, a retrieved chunk can't be cited back to its source — a user (or a downstream grounding check, see [RAG Techniques — Junior](../rag-techniques/junior.md)) has no way to verify where an answer came from. Without `updated_at`, there is no way to answer "is this still current?" at all — not even approximately.

## Core Concept 3 — A Small, Concrete Example: a 50-Document Internal FAQ

A team ingesting 50 internal FAQ pages designs this schema:

```json
{
  "document_id": "faq-042",
  "chunk_id": "faq-042#chunk-1",
  "source_uri": "https://wiki.internal/faq/042",
  "title": "How do I request time off?",
  "created_at": "2023-06-01",
  "updated_at": "2024-09-10",
  "source_type": "confluence-page",
  "owner": "hr-team",
  "content_hash": "sha256:7c3f...",
  "text": "Time-off requests must be submitted at least 5 business days in advance through the HR portal..."
}
```

This is deliberately kept separate from the chunk's embedded `text` — metadata fields are stored as structured, filterable attributes in the vector database (see [Embeddings and Vector Databases — Middle](../embeddings-and-vector-db/middle.md) for how metadata filtering interacts with search), not embedded into the text itself. A query like "show me only HR policies updated this year" becomes a metadata filter (`owner=hr-team AND updated_at > 2024-01-01`) combined with the similarity search, not something the embedding model has to somehow infer from prose.

## Core Concept 4 — Common Mistakes

1. **No `updated_at` field.** Without it, there's no way to tell a current policy from one that's three years stale — every retrieved chunk looks equally authoritative regardless of age, and a user has no signal to question an outdated answer.
2. **No `source_uri`.** A generated answer with no traceable source can't be verified or corrected at the source — if the answer is wrong, nobody knows which document to go fix.
3. **Embedding metadata into the chunk text instead of storing it as structured fields.** Writing `"[HR Team, updated 2024-09-10] Time-off requests must be..."` directly into the embedded text pollutes the embedding (the model now represents "HR Team" and a date as part of the semantic content) and makes filtering impossible — a filter needs a real field to filter on, not text buried inside a paragraph.
4. **No deduplication awareness.** The same document uploaded from two different source systems (an old wiki export and its live Confluence replacement) produces two separate, undated-relative-to-each-other chunks that can both be retrieved for the same query, sometimes contradicting each other — this is covered in depth in [middle.md](middle.md).
5. **Treating `document_id` and `chunk_id` as the same thing.** A document with 20 chunks needs one stable `document_id` shared across all of them (so "how many source documents do we have" is answerable) and 20 distinct `chunk_id`s (so a citation points to the specific passage, not just "somewhere in this document").

## Apply it

1. Pick a small, well-defined document set you have access to (team wiki pages, a policy folder, a FAQ) — 10 to 50 documents is enough.
2. Design a metadata schema covering at minimum the fields in Core Concept 2, adapted to what actually exists for your document set (not every source system provides an `owner` field cleanly — note where you'd have to infer or default it).
3. Manually populate the schema for 5 real documents from your set.
4. Write two example filtered queries your schema would support (e.g., "documents owned by team X, updated in the last 6 months") and confirm each maps cleanly to a metadata filter.
5. Identify one document in your set that exists in more than one form (a draft and a published version, or copies in two systems) and note what your schema would need to tell them apart.

## Verify your work

- Every chunk in your populated example has a distinct `chunk_id` and shares a common `document_id` with its sibling chunks from the same document.
- Your two example filtered queries can be expressed as a metadata filter without needing to parse or search the chunk's embedded text.
- You can trace any one chunk back to a real, dereferenceable source location via `source_uri`.
- For the duplicate-document case you identified, you can state which metadata field(s) would let a retrieval system tell the two versions apart (or flag them as a duplicate to resolve).

## Review questions

- Why does a RAG knowledge base need explicit, structured metadata that a human-browsable folder of documents doesn't?
- What specifically breaks if `updated_at` is missing from every chunk's metadata?
- Why does embedding metadata directly into chunk text (instead of storing it as a separate field) make filtering harder, not just messier?
- What is the difference in purpose between `document_id` and `chunk_id`, and why does a schema need both?
