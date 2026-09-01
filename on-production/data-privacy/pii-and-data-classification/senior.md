# PII and Data Classification — Senior

<!-- level-focus -->
At senior level, focus on this question:

> What invariant guarantees that classification metadata survives every copy, derivation, and pipeline hop a piece of restricted data will ever pass through — and what evidence proves that invariant holds today, not just at design time?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core Concept 1 — Anchor Classification to Invariants, Not to Tables

A middle-level classification scheme is organized around datasets: this table is confidential, that joined view is restricted. At senior level, the organizing question changes: **which invariant does the classification scheme actually guarantee, across every system the data can reach?** An invariant is a property that must hold regardless of which team built which pipeline — not "this table is tagged restricted" but "restricted data is never readable by a system that doesn't enforce the restricted-tier access control, no matter how it got there."

Three invariants worth naming explicitly for a classification system:

| Invariant | What it rules out |
|---|---|
| Classification metadata travels with the data through every copy, join, and derivation | A restricted field silently arriving in an unclassified destination just because a generic ETL job copied it |
| No dataset combines a direct identifier with sensitive-category data without an explicit, reviewed decision | An analytics join accidentally producing a re-identifiable, health-adjacent dataset that nobody signed off on |
| Every restricted-tier field has a named accountable owner who can answer "where does this field go" at any time | A field whose classification is "restricted" on paper but whose actual blast radius nobody can describe |

A table-level classification scheme is *done* when every table has labels. An invariant-level scheme is *done* when every invariant has a *mechanism* enforcing it — not a description of the rule, but something (a pipeline check, a schema registry that rejects untagged writes, an ownership registry) that actually stops the violation or reliably flags it.

## Core Concept 2 — Correlated Failure: the Metadata-Losing Pipeline

The classification failures that cause real incidents rarely come from one engineer forgetting to tag one column. They come from **shared infrastructure that doesn't understand classification metadata at all**, silently stripping it from everything that passes through:

- A generic ETL tool that copies tables by column name and type has no concept of a `pii`/`tier` annotation — it copies the *data* and drops the *metadata*, because metadata isn't part of its contract.
- A schema-on-read format (a JSON blob column, a wide feature vector, an embedding) has no per-field boundary at all once the source fields are flattened into it — the classification that applied to the *inputs* has nowhere to attach on the *output*.
- A shared caching layer or search index, built once and reused by a dozen teams, was designed before classification tagging existed in the org, so nothing in its write path even has a slot for the tag.

```mermaid
sequenceDiagram
    participant Src as Users Table<br/>(email: restricted)
    participant ETL as Generic ETL Job
    participant FS as Feature Store
    participant ML as Recommendation Model
    Src->>ETL: copy columns by name/type
    ETL-->>FS: writes raw values, no tag metadata
    FS->>ML: serves feature vector
    Note over FS,ML: classification lost at ETL hop;<br/>nothing downstream knows this feature<br/>was ever restricted
```

None of the individual teams here made an obviously wrong decision. The ETL job does exactly what ETL jobs do. The feature store does exactly what feature stores do. The failure is that **no single component owned propagating the tag across the hop**, and the correlated-failure lesson is the same one that applies to any shared piece of infrastructure: ask explicitly what crosses it and whether the thing crossing carries the metadata that matters, rather than assuming it does because the data itself arrived intact.

## Core Concept 3 — The Hard Category: Silent Declassification

A **silent declassification** is the classification-system analogue of a gray failure: nothing errors, no alert fires, and the data keeps flowing — it has just quietly lost the label that was supposed to control who can read it. It is hard precisely because every individual step looks correct:

- A restricted field is exported to a spreadsheet for a one-off analysis; the spreadsheet has no classification concept at all, and six months later it's sitting in a shared drive folder with a permissive sharing setting.
- A derived feature — "average order value in the last 90 days" — is computed from a `restricted` field (payment records) but the derivation itself is treated as new, unclassified data, because nobody defined whether an aggregate of restricted data is still restricted.
- A machine-learning model trained on sensitive-category data produces embeddings that are, in principle, invertible enough to leak information about the training data — but the model artifact itself was never classified as anything, because "a model" doesn't look like "data."

The senior-level catalog entry for a silent declassification names not just where it happened but **why nothing caught it** — the same discipline as naming why a health check missed a gray failure. If the honest answer to "how would we know this is happening right now?" is "we wouldn't," that is itself the finding, and detection becomes the first action item, ahead of any fix.

## Core Concept 4 — Evidence Over Assumption

A classification scheme validated only by asking engineers to self-report tags reflects what people remember to declare, not what the data actually is. Validate it instead with:

- **Content-based discovery scanning**, not name-based assumption. A column named `notes` or `metadata` reveals nothing from its name; a scanner that samples actual values for identifier-shaped patterns (email formats, government-ID formats, phone-number formats) catches sensitive content that a name-only review would miss entirely, and catches it in places nobody thought to classify because nobody thought that table held personal data at all.
- **Lineage tracing from source to every live destination**, not from an architecture diagram drawn six months ago. A data-catalog or lineage tool that tracks actual write paths shows which destinations a restricted field really reaches today, including the ad-hoc export nobody remembers approving.
- **Reconciliation against real incidents.** Every classification-related incident (a field found somewhere it shouldn't have been, an access review turning up an unexpected reader) should map back to either confirming an existing invariant enforcement or exposing a gap in it. A classification scheme with zero incidents traced back to it either belongs to a very young pipeline or hasn't been checked against reality.

Treat every "restricted" or "confidential" tag as a claim with a confidence level: "enforced by a mechanism I can point to," "enforced by convention only," or "asserted, never checked." Prioritize checking the asserted ones that touch the highest-value invariant first, rather than trusting that a tag existing somewhere means the invariant it implies actually holds.

## Core Concept 5 — Cross-Component Scenario: Designing a Feature Store's Classification Contract

A platform team is building a feature store that will serve features to several ML models, sourced from `users`, `support_tickets`, and `payment_records` — the last of which contains restricted, sensitive-category fields. Two plausible designs for how the feature store handles classification:

| Design | Behavior | Trade-off |
|---|---|---|
| **A: Mechanical propagation** — every feature inherits the tier of its highest-classified input field, automatically | Fast to ship; no manual review step slows down adding a new feature | Doesn't handle derived/aggregate features correctly — an "average payment amount" feature mechanically inherits `restricted` from its input, even though a well-aggregated statistic over enough users may carry far less individual risk than the raw field. Over time this either produces so many restricted features that the store becomes unusable, or teams quietly reclassify things downward without review to get their work done |
| **B: Reviewed publication gate** — every new feature requires an explicit classification decision before it's published, informed by but not mechanically derived from its inputs | Correctly separates "this aggregate is genuinely less risky than its inputs" from "this raw pass-through field is exactly as risky as its source," and creates a paper trail of who decided what | Adds latency and a review bottleneck to shipping every new feature; without a fast-path for the common case (an unambiguous pass-through of an already-classified field), the review step becomes the thing people route around |

Neither design is free. Design A optimizes for velocity and correctly propagates classification for simple pass-through features, but has no mechanism for the aggregate/derivation judgment call that actually needs a human. Design B gets that judgment call right but only survives if the review step is fast for the 90% of features that are unambiguous pass-throughs — otherwise it becomes exactly the kind of friction that drives silent workarounds described in Core Concept 3. The senior-level resolution is usually a hybrid: mechanical propagation as the default for direct pass-through fields, with a required review gate specifically triggered when a feature is a derivation or aggregate rather than a copy — narrowing the expensive step to the cases that actually need judgment.

## Core Concept 6 — Questions That Expose Weak Assumptions

Before trusting a classification architecture, ask the questions that surface what hasn't actually been tested:

- "What happens when this data is copied by a tool that has no concept of classification metadata at all?" — most classification schemes are only validated against the pipelines that were built with classification in mind.
- "Is an aggregate or derived value computed from restricted data still restricted — and who decided that, explicitly?" — an unanswered version of this question means every ML feature and every report is an unreviewed guess.
- "If a restricted field ended up in an unapproved destination today, how would we find out — from a scanner, or from an incident?" — an honest "from an incident" answer means detection, not just prevention, needs investment.
- "Which of our shared infrastructure components were built before classification tagging existed, and do they silently drop it?" — surfaces the correlated-failure category from Core Concept 2 before it causes a real leak.
- "Who is the named, accountable owner for this restricted field's blast radius, right now?" — if the honest answer is "nobody specific," that is itself the finding.

## Core Concept 7 — Recovery and Evolution

A classification architecture is never finished; it needs explicit triggers for revisiting it: onboarding a new data source, introducing a new derived-data pipeline (a feature store, an ML training set, a new export format), a schema-on-read field being added where per-field tags can't attach, or a discovery-scan finding sensitive content in a table nobody had classified. Treat every one of these as a scheduled re-evaluation point, not a one-time setup task — and treat "our scan found unclassified PII in a table we thought was clean" as a finding to record and act on, not an embarrassment to quietly fix and forget, because the next revision of the scheme is only as good as what the last gap taught you.

---

## Real-World Examples

- **A generic ETL tool exposed as the weak link.** A lineage trace, run after an access review turns up an unexpected reader of a restricted field, shows the field passed through a shared, years-old ETL job with no classification awareness — exactly the correlated-failure pattern from Core Concept 2, invisible until someone traced the actual write path instead of trusting the architecture diagram.
- **A discovery scan finds what a name-only review missed.** A content-based scanner flags a `metadata` column in an old internal tool as containing government-ID-shaped strings; the column had never been classified because its name gave no indication, and a name-only review five different times had passed over it.
- **A hybrid feature-store design survives contact with reality.** The platform team ships Design A (mechanical propagation) with a review gate triggered only on aggregation/derivation, from Core Concept 5; six months later the review queue for genuinely novel derived features stays small enough that nobody routes around it, while pass-through features ship without friction.

## Common Mistakes

- **Validating a classification scheme only against pipelines built with classification in mind.** Legacy and shared infrastructure that predates the scheme is exactly where metadata silently drops, and it's invisible unless specifically checked.
- **Treating an aggregate or derived feature as automatically safe (or automatically as risky as its inputs) without an explicit review.** Both extremes are guesses until someone actually decides and records the decision.
- **Relying on column names for discovery instead of content-based scanning.** A column called `notes` or `data` tells you nothing about what's actually inside it.
- **Choosing a review-gate design with no fast path for unambiguous cases.** A gate that adds the same friction to every feature, novel or not, gets routed around, which is worse than no gate at all.
- **Treating classification architecture as a one-time project.** Without explicit re-evaluation triggers tied to new sources, new derived pipelines, and scan findings, the scheme drifts out of sync with the system within months.

---

## Apply it

1. Take a data pipeline you know that involves at least one hop through shared infrastructure (a generic ETL tool, a cache, a search index, a feature store), and trace whether classification metadata actually survives that hop or silently drops.
2. Name one invariant your classification scheme is supposed to guarantee (using Core Concept 1's table as a starting point) and identify the specific mechanism — not just the documented rule — that enforces it today.
3. Pick one derived or aggregated field in a system you know and explicitly decide, with written reasoning, whether it should inherit its inputs' classification or carry a different one.
4. Run the five weak-assumption questions from Core Concept 6 against your pipeline and write down which question exposed the shakiest assumption.
5. Design a fast path for unambiguous pass-through classification alongside a slower review path for derived/aggregate data, and state what makes a feature qualify for the fast path.

## Verify your work

- Your traced pipeline names the exact hop where classification metadata would be lost, not a vague "somewhere downstream."
- The invariant you named has a concrete enforcement mechanism you can point to — a check, a registry rejection, an ownership record — not just a written policy.
- Your derived-field decision is recorded with reasoning that a teammate could evaluate and disagree with, not just a gut call.
- At least one weak-assumption question surfaces a real gap in your own pipeline, not a hypothetical one.
- Your fast-path criteria are specific enough that someone could apply them to a new feature without asking you personally.

## Review questions

- Why does anchoring a classification scheme to invariants change what counts as "the scheme is complete"?
- What makes a silent declassification harder to detect than a field that was simply never tagged?
- Why can mechanically propagating classification tags produce worse outcomes than an explicit review, specifically for derived or aggregated data?
- What evidence turns a classification tag from an assumption into something you can trust when designing a new pipeline?
