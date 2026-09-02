# RAG Techniques — Junior

<!-- level-focus -->
At junior level, focus on this question:

> Given a small set of documents, can you build a retrieve-then-generate pipeline and show — with evidence, not assumption — that the answer came from the retrieved text?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core Concept 1 — Vocabulary: Retrieval, Augmentation, Generation, Grounding

RAG is three steps chained together, and the words for each step get used loosely:

- **Chunk** — a piece of a source document, small enough to embed and retrieve individually. A 40-page PDF isn't one retrievable unit; it's split into many chunks.
- **Retrieval** — given a query, finding the chunks most likely to contain the answer, usually by comparing the query's embedding to each chunk's embedding (see [Embeddings and Vector Databases](../embeddings-and-vector-db/junior.md) for how that comparison works).
- **Augmentation** — inserting the retrieved chunks into the prompt sent to the language model, alongside the user's question and instructions.
- **Generation** — the model producing an answer, conditioned on the augmented prompt.
- **Grounding** — the property that the generated answer is actually supported by the retrieved chunks, not invented. An ungrounded answer that happens to be correct is still a failure of the pipeline — it got lucky.
- **Hallucination** — the model stating something as fact that isn't supported by the retrieved context (or by anything at all). RAG reduces hallucination risk; it does not eliminate it — a model can be handed the right chunk and still ignore it.

The one-line relationship: **retrieval finds evidence, augmentation shows the model the evidence, generation produces an answer the evidence should be able to justify.**

## Core Concept 2 — The Loop, End to End

```mermaid
flowchart LR
    Q[User query] --> E[Embed query]
    E --> S["Similarity search over chunk embeddings"]
    S --> TopK["Top-k chunks"]
    TopK --> P["Build prompt: instructions + chunks + query"]
    P --> LLM["LLM generates answer"]
    LLM --> A["Answer, ideally with citations"]
```

At index time (before any query arrives), documents are split into chunks and each chunk is embedded and stored — this is covered in depth in [Knowledge Base Design](../knowledge-base-design/junior.md) and [Embeddings and Vector Databases](../embeddings-and-vector-db/junior.md). At query time, the steps above run: embed the query with the *same* embedding model used to embed the chunks, search for the closest chunks, and hand a fixed number of them (top-**k**, commonly k=3 to k=8 for a first pass) to the model along with the question.

## Core Concept 3 — Building a Minimal Pipeline

A minimal pipeline, shown as pseudocode independent of any specific framework:

```python
# 1. Index time — run once per document set, rerun when documents change
chunks = split_into_chunks(documents, chunk_size=500, overlap=50)  # tokens
chunk_embeddings = [embed(c.text) for c in chunks]
vector_store.upsert(chunk_embeddings, metadata=[c.source for c in chunks])

# 2. Query time — run once per user question
query_embedding = embed(user_question)
top_chunks = vector_store.search(query_embedding, top_k=5)

prompt = f"""Answer the question using ONLY the context below.
If the answer isn't in the context, say you don't know.

Context:
{format_chunks(top_chunks)}

Question: {user_question}"""

answer = llm.generate(prompt)
```

Two details that separate a working pipeline from a broken one, both visible in this pseudocode:

1. **The embedding model must be identical at index time and query time.** A query embedded with `text-embedding-3-small` searched against chunks embedded with a different model (or even a different version) produces meaningless similarity scores — the vectors don't live in a comparable space. This is covered in depth as *embedding drift* at senior level in [Embeddings and Vector Databases](../embeddings-and-vector-db/senior.md).
2. **The prompt explicitly instructs the model to answer only from context and to admit not knowing.** Without this instruction, a capable model will often fall back to its own parametric knowledge when the retrieved context is thin or irrelevant — which defeats the purpose of retrieving in the first place and is indistinguishable, from the user's side, from a correct grounded answer until it's wrong.

## Core Concept 4 — A Small, Concrete Example

Document set: five internal FAQ entries about a company's expense-reimbursement policy. One entry says: *"Reimbursement requests must be submitted within 30 days of the expense. Requests submitted after 30 days are not processed."*

Query: *"How long do I have to submit an expense reimbursement?"*

- Embed the query, search the 5 chunks, the reimbursement-deadline chunk scores highest similarity.
- The prompt includes that chunk plus the question.
- Expected answer: *"You have 30 days from the date of the expense to submit a reimbursement request."*

This is checkable two ways, and both matter:

- **Correctness** — does the answer state 30 days, not a hallucinated number?
- **Groundedness** — does the answer trace back to the retrieved chunk, or did the model happen to know this from training data? Test this by asking a question whose answer is *not* in any of the 5 chunks (e.g., "What's the reimbursement policy for a different company you've heard of?") — a well-grounded pipeline says it doesn't know; an ungrounded one may answer from general knowledge and give you false confidence in queries you didn't test.

## Core Concept 5 — Evaluating the Pipeline by Hand

At this level, evaluation doesn't need a framework — it needs a small, deliberate test set:

1. Write 8–10 question/expected-answer pairs where you know, because you wrote the documents, exactly which chunk should be retrieved and what the answer should say.
2. Run each question through the pipeline and record: which chunk(s) were retrieved, and whether the generated answer is correct and grounded in them.
3. Compute two numbers by hand:
   - **Retrieval hit rate** — for how many questions was the correct chunk actually in the top-k retrieved set? (If the right chunk isn't retrieved, no prompt engineering downstream can fix the answer.)
   - **Answer accuracy given correct retrieval** — of the questions where the right chunk *was* retrieved, how many got a correct, grounded answer?

Separating these two numbers is the single most useful habit to build now — it tells you whether a wrong answer is a retrieval problem or a generation problem, which is exactly the diagnostic skill built out fully at senior level.

## Common Mistakes

1. **Skipping chunking — putting whole documents in the prompt.** Works for a 5-document toy set, breaks the moment documents are large or numerous: you either blow the context window or bury the relevant sentence in irrelevant surrounding text, both of which hurt the model's ability to use it.
2. **Picking top-k arbitrarily.** k=1 misses the answer when it's split across two chunks; k=20 fills the context with noise and (per Core Concept 3) increases the chance the model answers from parametric memory instead of the crowded context. Start at k=3–5 and adjust based on the hit-rate measurement in Core Concept 5, not intuition.
3. **No instruction to stay grounded.** Without an explicit "answer only from the context, say so if you don't know" instruction, you cannot tell a genuinely grounded answer from a lucky guess — see Core Concept 4's own-knowledge test.
4. **Testing only on easy questions the model could answer without retrieval at all.** If every test question is something a general-purpose model already knows from training (e.g., "what is reimbursement"), you're not testing your pipeline — you're testing the base model, and you'll believe the pipeline works when in fact retrieval is silently broken or unused.
5. **Ignoring citations.** Not returning *which* chunk supported the answer makes every wrong answer a mystery. Ask the model to cite the chunk ID or source it used, even at this level — it costs a prompt-template line and turns every failure into a diagnosable one.

## Apply it

1. Take 5–10 short documents (internal notes, a FAQ, a policy doc — anything you can split into distinct facts).
2. Split them into chunks (even a crude fixed-size split is fine at this level), embed each chunk, and store them in a vector store or even an in-memory list of (chunk, embedding) pairs.
3. Build the query → embed → search → prompt → generate loop from Core Concept 3, including the "answer only from context" instruction.
4. Write 8–10 question/answer pairs where you know the ground truth, and one question whose answer is deliberately *not* in any document.
5. Run all of them through the pipeline and record retrieval hit rate and answer accuracy separately, per Core Concept 5.

## Verify your work

- For each test question, you can name which chunk(s) were retrieved and confirm whether that's the chunk that actually contains the answer.
- Retrieval hit rate and answer accuracy are recorded as two separate numbers, not one blended "pipeline worked / didn't" judgment.
- The question with no answer in the documents produces an "I don't know" response, not a confident invented answer.
- You can point to the specific line in the retrieved chunk that supports each correct answer.

## Review questions

- What is the difference between retrieval hit rate and answer accuracy, and why does separating them matter when a pipeline gives a wrong answer?
- Why must the query and the stored chunks be embedded with the same embedding model?
- What does asking a question with no answer in the document set actually test, that a normal correctness question does not?
- Why does an instruction to "answer only from context" change what a groundedness failure looks like?
