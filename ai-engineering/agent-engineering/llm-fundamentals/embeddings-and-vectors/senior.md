# Embeddings and Vectors — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Can you tell "similar" from "relevant" apart, diagnose the failure modes of a vector pipeline, and prove retrieval quality with a metric?

---

## Similarity ≠ relevance — the core failure

- Nearest-neighbor returns the most *textually similar* chunks — the user wanted the most *relevant answer to their question*. These diverge constantly:
  - The query describes a **problem**; the nearest chunk is the same problem's **documentation page title** — related, useless as an answer.
  - The nearest chunk is a **FAQ that mentions the topic without the solution**, beating the chunk with the actual fix.
- This is a property of the geometry, not a bug you patch — you manage it with ranking layers, better chunking, and hybrid search, not by "fixing the embeddings."

## The failure modes, named

- **Domain mismatch**: a general-purpose embedding model clusters legal, medical, or code jargon poorly — everything looks distant. Symptom: all similarity scores are low and rankings feel arbitrary.
- **Bad chunking resurfacing**: the right answer exists but spans a chunk boundary or sits inside an over-large chunk, so it's never the nearest. Symptom: the correct document is in top-20 but never top-3.
- **Query–document style mismatch**: users ask questions ("how do I…"), docs are written as prose. Embedding the question as-is underperforms. Fix: rephrase queries or store question-style summaries per chunk.
- **Stale index**: documents updated, embeddings not re-generated. Symptom: search confidently returns outdated content.

## Measuring retrieval with recall@k

- **recall@k**: of the chunks a human judged relevant for a set of test queries, what fraction appear in the top k results?
- Minimal practice: hand-label ~30–50 query→relevant-chunk pairs, run them through the pipeline, compute recall@5 (or @10). One number, comparable across changes.
- Improvements are only real if recall@k moves: chunking tweaks, model swaps, hybrid weighting — measure each against the same labeled set (the eval discipline behind this is [Datasets and Graders](../../agent-evaluation/datasets-and-graders/)).

## Changing embedding models = re-embed everything

- Vectors from different models live in incompatible spaces. Switching models (even versions) means re-embedding the **entire corpus**, then swapping — and old/new vectors must never mix.
- Plan it as a migration: build a new index alongside the old, verify recall@k on the new, cut over atomically, keep the old index until confidence is proven.

## Common Mistakes

- **Reading "similar but wrong" results as a bug to patch.** It's the geometry working as designed; the fixes are architectural.
- **Tuning the pipeline with no labeled queries.** Every change is vibes; recall@k is what turns retrieval work into engineering.
- **Mixing old and new vectors during a model migration.** Rankings degrade confusingly and nobody can tell why.
- **Diagnosing everything as "bad embeddings."** Chunking, query style, and staleness each produce different symptoms — match the symptom to the cause.

## Apply It

1. Label 30 real queries with their relevant chunks; compute recall@5 for your current pipeline as the baseline.
2. Reproduce one failure: find a query where the top hit is similar-but-wrong, and classify which failure mode it is.
3. Check index staleness: sample 10 recently-edited documents and confirm their embeddings are current.

## Verify Your Work

- Retrieval quality is claimed with a recall@k number, not impression.
- Every observed failure is classified into a named mode before a fix is proposed.
- Any embedding-model change has a migration plan that never mixes vector spaces.

## Review Questions

- Why can the nearest chunk be the wrong answer even with perfect embeddings?
- What does recall@5 measure, and why is a labeled query set the minimum tooling for retrieval work?
- Why does changing embedding models require re-embedding the entire corpus?
