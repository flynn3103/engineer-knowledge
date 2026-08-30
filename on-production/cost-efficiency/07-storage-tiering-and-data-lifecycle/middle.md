# Storage Tiering and Data Lifecycle — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Given several data classes in one system with different access patterns, where should the tiering boundaries fall for each, and what trade-off decides how many lifecycle rules you actually implement versus how many you'd need to be theoretically optimal?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

*A junior engineer tiers one bucket correctly. A middle engineer decides how many buckets, rules, and exceptions a real system can carry before the policy itself becomes the maintenance burden.*

---

## Core Concept 1 — Derive boundaries from evidence, not intuition

The junior method matches a tier to an assumed access pattern. At this level, replace the assumption with measured evidence. Most object stores expose the data you need directly: S3 Storage Class Analysis, per-object last-accessed timestamps, or your own access logs joined against object age. Plot **read frequency against object age** and look for the knee in the curve — the age past which reads drop off sharply. That knee, not a round number like "30 days" chosen by habit, is where a transition belongs.

```
Reads per day
  │▓▓▓▓▓▓▓▓▓▓▓▓
  │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
  │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
  │▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░
  └───────────┴───────────────────────────► age (days)
              ▲
        the knee: transition here, evidenced by the drop,
        not chosen because it's a tidy number
```

If you don't have this telemetry yet, generating it (even a rough one-off query against access logs) is worth doing before writing the rule — a lifecycle policy based on a guess is a policy you'll have to redo once real numbers surface, and by then it may have already deleted something.

---

## Core Concept 2 — Compression and format choice as a second, composable lever

Tiering and compression are independent decisions that compound. For structured or semi-structured data (logs, event exports, analytics tables), the format itself often matters more than the tier: switching a nightly export from row-oriented JSON to a columnar format with a fast compression codec (Parquet or ORC with Snappy or Zstandard) frequently shrinks the stored footprint dramatically *before* tiering is even considered, and it also speeds up the infrequent reads that do happen because columnar formats let a downstream query skip columns it doesn't need. The order of operations that avoids waste:

1. Pick the right format/compression for the *access pattern* the data will have wherever it lives (don't compress in a way that makes an occasionally-hot-read job slow).
2. Then apply tiering on top, based on the age-vs-access-frequency curve from Concept 1.

Treat "wrong format, right tier" and "right format, wrong tier" as two distinct bugs you should be able to diagnose separately — conflating them makes cost regressions hard to root-cause.

---

## Core Concept 3 — Testing a lifecycle policy without waiting months

A lifecycle rule that transitions data at day 90 is not something you want to validate by waiting 90 days in production. Three practical techniques:

- **A scratch bucket/prefix with compressed timelines.** Apply the same rule shape but with day thresholds divided by 10 (day 3 instead of 30, day 9 instead of 90) against synthetic objects backdated with `LastModified`-style metadata where the provider allows it, or objects genuinely aged a few days, to confirm the *shape* of the rule (ordering, filters, expiration) before deploying the real thresholds.
- **Dry-run/shadow evaluation.** Some providers expose a way to preview which objects a rule *would* affect (via storage inventory reports or a scripted diff against the rule's filter) without it actually executing. Run this against your real, current object population and diff the result against what you expect.
- **Monitoring the transition count, not just the rule's existence.** After deploying, track "objects transitioned per day" against the expected volume from your ingestion rate. A rule that stops matching anything (a filter bug, an IAM permission change, a prefix that no longer matches how objects are being written) is silent by default — nothing errors, it just quietly does nothing.

This is the same testability instinct you'd apply to any automated background process: verify the mechanism independently of waiting for its real-time trigger to fire naturally.

---

## Core Concept 4 — Under- and over-application signals

**Signs you have too few tiers/rules (under-application):**
- A single "keep everything in Standard/Hot forever" default, with cost as the only signal anyone notices — usually discovered by finance, not engineering.
- Data with a clearly cold access pattern (old backups, superseded exports) sitting in the same tier as actively-served data, with no one having looked at the age-vs-access curve.

**Signs you have too many tiers/rules (over-application):**
- A dozen bucket-specific or prefix-specific rules, each hand-tuned, that nobody can recite from memory — an audit of "what happens to this data over its life" now requires reading rule XML/JSON across several buckets.
- Rules with overlapping or ambiguous filters where two rules could plausibly apply to the same object, and the actual behavior depends on provider-specific rule precedence nobody documented.
- Frequent surprise retrieval-latency incidents because the number of distinct tiers in play exceeds what any one engineer keeps a mental model of.

The trade-off middle engineers navigate: **more tiers and finer-grained rules save more money in theory, but each additional rule is a piece of state someone has to remember, audit, and get right.** A good working default is two or three tiering steps per data class (hot → warm → archive, with expiration), not a bespoke schedule per prefix — reserve extra granularity for data classes large enough that the savings clearly outweigh the added complexity.

---

## Core Concept 5 — Incremental adoption order

Roll tiering out data-class by data-class, ordered by favorable risk-to-reward ratio:

1. **Start with clearly low-risk, high-volume data** — raw ingestion logs, intermediate pipeline artifacts, old build outputs. Mistakes here are cheap: nobody's customer-facing path depends on immediate access to a two-year-old build log.
2. **Move to backups and snapshots** once the mechanism is proven — these are higher-stakes (a restore might be needed under pressure) but still not directly customer-facing.
3. **Save behavior-critical or compliance-sensitive data for last** — anything with a legal retention requirement, active customer access pattern, or contractual restore-time SLA. By the time you tier this, the mechanism, monitoring, and testing approach should already be proven on lower-stakes data.

---

## Core Concept 6 — Worked scenario across multiple components

An e-commerce platform has two data flows that both need tiering, and treating them identically would be a mistake:

**Flow A — order-event logs**, written by the order service to `s3://orders-events/raw/`:
- Read heavily by an analytics reprocessing job for the first 90 days.
- Required for 7 years to satisfy financial-record retention.
- Read pattern: many reads early, essentially none after day 90, except rare audits.

**Flow B — nightly database backups**, written by a backup job to `s3://orders-db-backups/nightly/`:
- Needed for point-in-time restore, so the last 35 days must stay quickly restorable.
- Older backups are kept 1 year for disaster-recovery compliance, then deleted.
- Read pattern: essentially never read unless there's an active incident — but when read, it must be *fast*, because a restore during an incident is time-critical.

```yaml
# Flow A: orders-events — tiering favors deep cost savings; reads become rare after day 90
rule: orders-events-tiering
prefix: raw/
transitions:
  - after_days: 30
    storage_class: STANDARD_IA
  - after_days: 90
    storage_class: ARCHIVE
expiration_days: 2555   # ~7 years

---
# Flow B: orders-db-backups — tiering favors restore speed over deepest savings
rule: orders-db-backups-tiering
prefix: nightly/
transitions:
  - after_days: 35
    storage_class: NEARLINE     # NOT archive — restores must stay fast
  - after_days: 365
    storage_class: COLDLINE
expiration_days: 400
```

Flow B deliberately stops at a "warm-ish" cold tier instead of following Flow A into deep archive, because the *cost of a slow restore during an incident* outweighs the marginal storage savings of the coldest class. This is the core middle-level judgment call: the same "old data" label does not imply the same tier, because the two flows have different failure costs if a read is slow.

A third component matters here too: the nightly analytics job that reads Flow A data must have its query scoped to `raw/` objects younger than 90 days, or it will start silently hitting archive-tier objects and either fail or incur unexpected retrieval latency and cost — a classic way tiering decisions leak into components that didn't originate them.

---

## Common Mistakes

- **Choosing transition days from habit instead of the access-frequency curve** — "30/90/365" applied everywhere regardless of what the data actually looks like.
- **Compressing after tiering instead of before**, missing the chance to shrink the footprint that then gets carried through every subsequent tier.
- **Treating every "old" data class the same** — collapsing backups (restore-time-sensitive) and logs (rarely restore-time-sensitive) into one policy shape.
- **No monitoring on transition volume**, so a broken filter goes unnoticed until a cost or audit review months later.
- **Skipping the low-risk-first rollout order** and tiering compliance-critical data first, before the mechanism has been proven anywhere.
- **Letting a downstream job's scope drift** so it starts scanning data that tiering has since made slow and expensive to read.

---

## Apply it

1. Pick two real or realistic data classes in a system you know (e.g., application logs and a nightly export) with genuinely different access patterns.
2. For each, sketch the age-vs-read-frequency curve from whatever evidence you have (metrics, logs, or a reasoned estimate) and mark where the knee falls.
3. Write two separate lifecycle-rule snippets reflecting those different knees, including at least one deliberate difference in how "cold" each goes (e.g., one stops at infrequent-access, the other reaches deep archive).
4. Identify one downstream consumer of each data class and state, in one sentence, how its query scope must respect the tiering boundary you just set.
5. Design a lightweight verification: what metric or check would tell you within a week, not a quarter, that a rule stopped matching objects as expected.

## Verify your work

- Each data class's lifecycle rule reflects a documented reason (the access-frequency evidence), not a copied default.
- A reviewer can point to the one component or job that would break first if a tiering boundary were set wrong, and explain why.
- The verification check you designed would catch a silently-broken rule within days, not after a billing cycle.
- Running the two rules against sample data of different ages produces the storage-class assignment you predicted for each age bucket.

## Review questions

- What evidence, beyond intuition, should decide where a tiering transition boundary falls?
- Why might two data classes that both count as "old" need different lifecycle policies?
- What is the risk of adding a bespoke lifecycle rule per bucket versus reusing a small, standard set of tiering steps?
- How would you detect that a lifecycle rule has silently stopped matching any objects?
