# Search and Retrieval — Junior

<!-- level-focus -->
At junior level, focus on this question:

> Given a question that should be answerable from a repo or a set of documents, can you use grep/regex/glob to find the exact relevant lines instead of pulling in whole files?

---

## grep is a tool, not a fallback

For our data-analyst agent working against a dbt repo, "which model defines `gmv_daily`?" is answered by one command, not by loading every `.sql` file into context:

```bash
rg -n "def gmv_daily|model.*gmv_daily" --type sql
```

- `rg`/`grep` do **exact and regex** matching — they find precisely what you asked for, with no approximation and no missed synonyms if the term is right.
- Returning **line numbers and a small context window** (`-A 3 -B 3` = 3 lines after/before) costs a fraction of the tokens that returning the whole file would cost, and gives the model exactly the span it needs.
- `glob` (e.g., `**/*.sql`) narrows *which files* to look in before searching their contents — combine narrowing with searching rather than searching everything.

```mermaid
flowchart LR
    A["Question with an exact term<br/>'gmv_daily'"] --> B["glob: narrow file set"]
    B --> C["grep: find exact matches"]
    C --> D["Return line + small context window"]
```

## When exact match is the right tool

- Looking for an **identifier**: a column name, function name, error code, config key, order ID.
- Looking for **where something is defined**, not "what does this concept mean."
- The corpus is **code, logs, or config** — text where meaning is tied to exact tokens, not paraphrase.

## When exact match falls short

- The question uses different words than the document ("revenue drop" vs. a doc that says "GMV decline") — a plain grep for "revenue drop" finds nothing even though the relevant doc exists. This gap is what [BM25](../middle.md) and later [RAG](../../rag-and-vector-decisions/) address.

## Trace one query by hand

For "find every place `refund_amount` is validated" in a sample repo:

1. Write the exact `grep`/`rg` command, including any file-type or path filter.
2. Predict how many matches you expect before running it.
3. Run it. If it returns hundreds of matches, that's a signal your pattern is too broad — narrow it (a file glob, a more specific regex) rather than returning all of it to the model.
4. Write the final line-number + snippet set you'd hand to the model — not the whole files.

## Comprehension check

- Why is returning a line number and a small snippet better than returning the whole file, for both accuracy and token cost?
- Give one example of a question where grep is the obviously correct tool, and one where it obviously is not.
- What's wrong with a search that returns 5,000 matches with no filtering, and what's one way to fix it?
- What does `glob` narrow, and why narrow before searching contents?
