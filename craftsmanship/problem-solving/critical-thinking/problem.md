# Critical Thinking — Problem

**What it is:** analyzing, evaluating, and reconstructing a claim or argument in a systematic way — questioning assumptions, checking evidence, and considering alternatives — instead of accepting the first confident-sounding sentence as fact.

## The mechanism: five moves, in order

- **Isolate the claim** — strip it down to one sentence, separate from the evidence or opinion wrapped around it.
  - "MongoDB will be faster here" is a claim. "MongoDB is known for being fast and lots of companies use it" is not evidence for that claim — it's the claim restated in different words.
- **Surface the assumption it depends on** — what has to be true for this claim to hold, that nobody has actually checked?
  - The MongoDB claim assumes your read/write pattern resembles the pattern MongoDB is fast at. That assumption is invisible until you name it.
- **Evaluate the evidence** — is there a real measurement, or just confident phrasing, popularity, or an anecdote?
  - "Benchmarked on our staging cluster with our real queries" is evidence. "Everyone's using it" is not — it's the appeal-to-popularity fallacy, and it says nothing about your workload.
- **Consider the alternative explanation** — what else could produce the same observation, and who benefits from this claim being true?
  - Errors spiked right after a deploy — the deploy is one explanation. A traffic spike or an upstream outage at the same time are others; check before concluding cause.
- **Reach and record the conclusion** — decide, and write down what evidence would change your mind later.
  - Not "we decided to migrate" — "we decided to migrate because X; we'll revisit if Y."

```mermaid
flowchart LR
    Claim --> Assumptions --> Evidence --> Alternatives --> Conclusion --> Claim
```

## Worked example

**The claim, in a design doc:** "We should switch the orders table from Postgres to MongoDB — it'll be faster for our use case."

- **Isolate:** MongoDB will be faster than Postgres *for our orders table and our query patterns* — not faster in general.
- **Assumption:** that our workload (mostly indexed lookups by `order_id`, range scans by `created_at`) behaves like the workloads MongoDB is known to be fast at.
- **Evidence offered:** "MongoDB is known for being fast" (reputation, not a measurement) and "lots of companies use it" (popularity, not performance for this workload). Neither is evidence for the specific claim.
- **Alternative:** the current Postgres queries might be slow because of a missing index, not because Postgres itself is the bottleneck — a five-minute `EXPLAIN ANALYZE` could rule this out before anyone touches the database engine.
- **Conclusion that would survive scrutiny:** "We ran our top 5 production queries against a MongoDB replica seeded with a 30-day snapshot. The `created_at` range scan (180ms p95 on Postgres) ran at 95ms with a compound index on MongoDB, and write latency was comparable. We're migrating on that basis; we'll revisit if p95 write latency exceeds 20ms in production."

## Evaluate before you call it done

A conclusion built this way should pass four checks:

- **Falsifiable** — can you state what evidence would prove this claim wrong?
- **Sourced** — is the evidence direct (measured on your system) or indirect (someone else's benchmark, a blog post, an anecdote)?
- **Alternative-tested** — did you consider at least one other explanation for the same observation?
- **Recorded** — is the reasoning written down somewhere it can be checked later, not just remembered?

Continue to [Mistake](mistake.md).
