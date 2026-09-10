# Compaction and Memory — Professional

<!-- level-focus -->
At professional level, focus on this question:

> Can you define what memory persists across separate runs of an agent (not just within one run), its expiry/TTL policy, and the privacy boundary that governs what's allowed to persist at all?

---

## Within-run vs. across-run memory

Everything in the earlier levels of this topic is about one run's context outgrowing one window. Long-horizon memory is a different scope: what does the agent remember on **Tuesday's** run that it learned on **Monday's**?

- **Within-run compaction** (junior-senior levels): summarization, scratchpads, handoff artifacts — all scoped to one task's lifetime.
- **Across-run memory**: a persistent store (a database, a file, a memory-specific service) that survives the process ending and is deliberately re-loaded into a *future*, separate run's context.

For the data-analyst agent: "GMV dropped in SG last Tuesday due to a pricing bug, confirmed and fixed" is a fact worth persisting — if the same anomaly-shaped question comes up again next month, the agent should be able to recall that this exact incident was already investigated and resolved, rather than re-running the full investigation from zero.

## Lifecycle: what persists, and for how long

| Question | Design decision required |
|---|---|
| What gets written to long-term memory? | Not every fact discovered in a run — define a threshold (e.g., "confirmed conclusions," not "every query tried") the same way middle-level compaction defines must-survive categories. |
| Who/what decides it's worth persisting? | An explicit step (a rule, or a model call with a specific prompt) — not "whatever happened to still be in context when the run ended." |
| TTL / expiry | Some facts age out — "GMV was down last Tuesday" is true forever as a historical fact, but "current pricing config" from three months ago may now be wrong and actively misleading if recalled without a freshness check. |
| Where does it live? | A separate memory store, indexed for the *next* run's retrieval — this is where [Search and Retrieval](../../search-and-retrieval/) and [RAG and Vector Decisions](../../rag-and-vector-decisions/) apply again, now to the agent's own memory of itself rather than to an external corpus. |

## The privacy and retention boundary

Persisting anything across runs is a data-retention decision with real consequences, not just an engineering convenience:

- **What's allowed to persist at all** — a fact about a public dataset's schema is low-risk to retain; a fact that includes a specific customer's PII surfaced during an investigation is not, and needs an explicit retention policy (or an explicit rule that it never persists past the run it was seen in).
- **Who can read persisted memory** — if memory is shared across agents or across users, the same access-control-at-query-time discipline from [Search and Retrieval — Professional](../search-and-retrieval/professional.md) applies: a memory entry written during one user's session must not leak into another user's session unless that's an explicit, reviewed design choice.
- **Auditability** — for any persisted memory that influenced a later answer, it should be traceable which prior run wrote it and when, the same way a decision needs an audit trail in any regulated system.

## Comprehension check

- What's the difference in scope between within-run compaction and across-run memory?
- Why can't "whatever's still in context when the run ends" be the rule for what gets persisted long-term?
- Give an example of a fact that should have a TTL/expiry rather than persisting indefinitely, and explain why.
- What access-control question must be answered before memory is shared across multiple users or agents?
