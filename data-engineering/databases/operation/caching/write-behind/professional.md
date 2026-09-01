# Write-Behind — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How do real durable-log systems (the write-ahead log inside a database
> itself) formalize the "buffer now, flush later" pattern, and what does
> `fsync`'s actual guarantee (and its historical failures) teach about
> trusting an ack?

Prerequisite: [`senior.md`](senior.md).

---

## Write-behind is what every database's own WAL already is

Strip away the "cache" framing: write-behind (buffer in fast storage,
batch-flush to slow durable storage, ack the caller early) is exactly the
internal architecture of a database's own **write-ahead log plus group
commit** (see the Transactions & ACID professional page) — the WAL buffer in
memory is the "fast buffer," the periodic `fsync` to the WAL file is the
"batch flush," and the client ack after WAL `fsync` (not after the data
pages are written) is functionally identical to a write-behind cache's ack.
The professional-level insight: **you're not choosing whether to accept a
durability gap — every system with any buffering at all has one; the
question is precisely how wide it is and what mechanism bounds it.**

## `fsync` doesn't mean what most engineers assume

The infamous **PostgreSQL `fsync` bug (2018)**, found by Craig Ringer and
documented extensively by the Postgres community, revealed that on Linux,
if `fsync()` fails (e.g. due to an underlying storage error), the kernel
**may mark the error as handled internally and clear the dirty-page flag**,
meaning a **subsequent `fsync()` call reports success** even though the
original write never made it to disk — silently violating the durability
assumption every database built on `fsync` implicitly relies on. This is a
staff-level cautionary case study: an "acked, durable" write's actual
guarantee is bounded by the correctness of every layer beneath your
application, including kernel behavior you don't control and historically
got wrong in ways that took years to discover and fix (`errseq_t` was
introduced in Linux 4.13 specifically to address this).

```mermaid
flowchart LR
    App["Write acked as\n'durable' after fsync()"] --> Kernel["Kernel: fsync() call"]
    Kernel --> Disk["Disk write actually fails"]
    Disk -.pre-4.13 Linux: error\nsilently cleared.-> Kernel2["Next fsync() call\nreports SUCCESS"]
    Kernel2 --> False["Application believes\ndata is durable.\nIt isn't."]
```

## Kafka's producer `acks` as a tunable write-behind buffer boundary

Kafka's producer `acks` setting is a direct, explicit knob on exactly the
trade-off this topic is about: `acks=0` is pure write-behind (ack before the
broker even receives it — maximum throughput, maximum loss risk on broker
failure); `acks=1` acks after the leader partition writes to its local log
(survives a client crash, not a leader-broker crash before replication);
`acks=all` (with `min.insync.replicas` set appropriately) acks only after a
quorum of replicas have the message, converging toward the "durable,
replicated buffer" end of the spectrum described in `senior.md`'s
escalation path — the professional-level point being that this is not three
arbitrary settings but three named points on the exact same fundamental
durability-vs-throughput continuum every write-behind system faces,
formalized as a first-class, documented API contract rather than an
implementation detail.

## Production checklist (staff-level)

1. **Never assume `fsync()` (or any "durable" acknowledgment API) is
   infallible** — know your kernel/filesystem version's handling of write
   errors, and specifically verify behavior around `errseq_t` semantics
   (Linux 4.13+) for any system where a silent fsync failure would be a
   serious incident.
2. **Treat every buffering layer in your stack (application write-behind
   cache, database WAL, OS page cache, disk controller cache) as a
   potential durability gap**, and explicitly trace the full chain for any
   system where "acked" must mean "actually durable" — a write-behind
   cache's durability guarantee is only as strong as the weakest link
   beneath it.
3. **Choose Kafka's `acks` (or an equivalent explicit durability knob in
   your messaging layer) deliberately per data class**, exactly as
   recommended for cache write-behind classification in `senior.md`/
   `professional.md`'s pipeline discussion — `acks=all` for anything where
   loss is unacceptable, `acks=1` or `acks=0` only where it's genuinely
   fine.
4. **In a postmortem for unexpected data loss after a crash, check every
   layer's actual durability semantics explicitly**, not just the
   application's write-behind logic — historically, some of the most
   surprising data-loss incidents in the industry trace to a kernel- or
   filesystem-level assumption that turned out to be false.
5. **Prefer well-audited, widely-deployed durable log implementations
   (Kafka, a database's own WAL) as your write-behind buffer** over a
   custom in-house implementation — the `fsync` case study above happened
   to one of the most scrutinized pieces of software in the industry;
   assume a homegrown equivalent has undiscovered gaps of its own.

## Cheat Sheet

```text
+------------------------------------------------------------------+
|               WRITE-BEHIND — INTERNALS & SCALE                      |
+------------------------------------------------------------------+
| Write-behind is structurally identical to a database's own WAL +      |
| group commit: buffer -> batch flush -> ack after buffer write, not     |
| after final durable storage. Every buffered system has this gap -     |
| the only question is how wide it is and what bounds it                |
+------------------------------------------------------------------+
| fsync() is not infallible: the 2018 Postgres/Linux fsync bug showed    |
| a failed fsync could be silently marked handled, so a LATER fsync      |
| call reports success for data that was NEVER written - fixed by        |
| errseq_t in Linux 4.13+. "Acked as durable" is bounded by every        |
| layer beneath your application, including the kernel                  |
+------------------------------------------------------------------+
| Kafka acks=0/1/all are three NAMED points on the exact same            |
| durability-vs-throughput continuum every write-behind system faces -   |
| choose per data class, deliberately, as a first-class API contract     |
+------------------------------------------------------------------+
```

## Test yourself

1. Explain why a database's WAL + group commit is, structurally, the same
   pattern as a write-behind cache, and identify the "buffer" and "final
   durable store" in each.
2. Research or recall: why did the 2018 Postgres fsync bug specifically
   cause data loss to go undetected, rather than causing an obvious error?
3. Design the `acks` and `min.insync.replicas` configuration for a Kafka
   topic carrying financial transaction events, and justify the choice
   against the durability/throughput continuum described here.

## Further Reading

- Craig Ringer / PostgreSQL mailing list — "Postgres's handling of fsync()
  errors" (2018, the original discovery and community response).
- The Linux kernel `errseq_t` documentation — the actual kernel-level fix.
- Kafka documentation — "Producer Configs: acks" and "Replication"
  (`min.insync.replicas`).
- See also: [Write-Through — professional](../write-through/professional.md),
  [Transactions & ACID — professional](../../../transaction/transactions-and-acid/professional.md).
