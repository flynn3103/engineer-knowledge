---
name: data-engineering-content
description: Use when writing or restructuring conceptual learning content under data-engineering/ (or any junior-to-professional knowledge-base topic in this repo, e.g. databases/data-modeling, distributed-system/consensus, event-streaming). Triggers on requests like "write this topic from junior to professional", "add a README/junior/middle/senior/professional for <concept>", "deep dive <concept> with diagrams", or "rewrite <folder> for data engineer". Produces the 5-file (README + junior/middle/senior/professional) structure used across programming-languages/golang, with Mermaid diagrams and data-engineering-specific framing for junior/middle/senior, and staff/principal-level systems-engineering depth for professional.
---

# Data Engineering Content Skill

Write conceptual deep-dive topics (leader election, relational modeling,
partitioning, backpressure, etc.) as a **5-file set per topic folder**, mirroring
the pattern already established in `programming-languages/golang/*/` and
`data-engineering/distributed-system/consensus/leader-election/`.

## File structure (per topic folder)

```
<topic-folder>/
  README.md        # index: 2 mermaid diagrams + level table, <100 lines
  junior.md         # what & why, naive/first approach, why it breaks
  middle.md         # the real mechanisms/algorithms, one worked example
  senior.md         # failure modes, trade-offs, how to make it safe/correct
  professional.md   # staff/principal-level internals, scale, production ops
```

Every file **must stay under 500 lines**. In practice the reference example
(`leader-election/`) runs 48/81/88/78/116 lines — aim for that range, not the
cap. Do not pad with 20-section templates (glossary, tricky-questions, 10-item
mistake lists, etc.) — that older, much longer style exists elsewhere in this
repo but is NOT what this skill produces.

## Required ingredients in every topic

1. **Data-engineering framing for junior/middle/senior**, not generic backend
   examples. Ground these three levels in real tools/systems a data engineer
   touches: Kafka (KRaft/ZooKeeper), Airflow, Flink, Spark, Debezium/CDC,
   Delta Lake/Iceberg, dbt, warehouses (Snowflake/BigQuery/Redshift), object
   storage, orchestration.
2. **At least 2 Mermaid diagrams total across the file set** — typically a
   `flowchart` in `README.md` (level progression + concept overview) and a
   `sequenceDiagram` or second `flowchart` in `junior.md`/`middle.md` showing
   the mechanism concretely (e.g. a sequence diagram of a naive approach
   failing). Add more in `senior.md`/`professional.md` when comparing
   approaches (e.g. two subgraphs side by side).
3. **"Test yourself" section at the end of junior/middle/senior**, 3–4
   questions, each ending with a link forward: `Continue to [\`middle.md\`](middle.md).`
4. **`README.md` contains**: the one-line pull-quote framing the concept, a
   level-progression flowchart, a concept-overview diagram, a 4-row table
   (Junior/Middle/Senior/Professional → guide link → "you are done when"), a
   short "Practice rule", and a "Related" section linking sibling topics.

## `professional.md`: staff/principal depth, NOT domain-flavored

This is the level that most differs from the others, and the one most
frequently written wrong. Rules specific to this file:

- **Write as general staff-level systems engineering knowledge, not "how a
  data engineer uses this."** Do not frame the whole page around pipelines,
  warehouses, or Kafka/Airflow the way junior/middle/senior are framed. A
  backend engineer, an SRE, or a database internals engineer should get full
  value from this page with zero data-engineering context.
- **Go under the hood of 2–4 named, real systems.** Reference the actual
  algorithm, data structure, or subsystem by name — e.g. Postgres's SIREAD
  locks and predicate locking for Serializable Snapshot Isolation, RocksDB's
  leveled vs. tiered compaction, the Linux page cache and `fsync` semantics,
  InnoDB's undo log and purge thread, etcd's boltdb backend, the JVM's
  concurrent mark-sweep internals. Prefer source-level or paper-level
  specificity over "some databases do X."
- **Cover scale and failure behavior with real bottlenecks**, e.g. what
  breaks first under 10x/100x load, what the actual numbers look like
  (latency, memory, IOPS), and what the failure mode looks like in
  production, not just in theory.
- **Cover production operability**: what metric you'd put on a dashboard,
  what a runbook entry looks like, what a postmortem for this subsystem
  reads like, what a staff engineer would ask in a design review.
- **End with**: a design/ops checklist (staff-level judgment calls, not
  beginner steps), an ASCII cheat-sheet block, "Test yourself" (staff-level
  scenario questions), and "Further Reading" that includes real papers,
  source code references, or engineering blog postmortems where they exist —
  not just vendor docs.

## Content progression (what goes in junior/middle/senior)

- **junior.md** — Define the problem in plain terms with a data-pipeline
  scenario. Show the obvious/naive first approach. Show *why* it breaks with a
  concrete diagram (sequence diagram works well for timing bugs). Do not yet
  introduce the fix — end on the open question, pointing to `middle.md`.
- **middle.md** — Introduce the real mechanisms/algorithms/options as a
  decision table or flowchart. Walk through one concrete, runnable-looking
  code example (Python/SQL/Go, pick whatever fits the topic) using the tool a
  data engineer would actually reach for (etcd, Spark, dbt, Kafka client,
  etc.). This is "how it actually works," not yet "how to make it safe."
- **senior.md** — The failure modes middle.md's approach still has, and the
  fix. Trade-off tables (e.g. TTL length, batch size, consistency level).
  This is where correctness/safety guarantees get established.

## Process for a new topic

1. Read the existing empty/stub folder (check for `.pages`, `.gitkeep`, or an
   existing thin `README.md`) to learn the folder's intended scope and any
   existing nav title.
2. Write all 5 files in one pass, keeping cross-links consistent
   (`README.md` → junior/middle/senior/professional; each level links forward
   to the next; `professional.md` has no forward link).
3. Verify line counts with `wc -l <folder>/*.md` and confirm every file is
   under 500 lines.
4. If restructuring an existing single long file, extract its content into
   the 5-file split rather than deleting information — redistribute sections
   into the level where they best fit per the progression above.

## Reference example

Read `data-engineering/distributed-system/consensus/leader-election/{README,junior,middle,senior,professional}.md`
in this repo before writing a new topic's junior/middle/senior — match its
tone, length, diagram density, and section shape. For `professional.md`
specifically, match the deeper, non-domain-flavored style described above
(post-dating that leader-election example, which predates this rule and
should eventually be upgraded too).
