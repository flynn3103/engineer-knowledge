# Producer-Consumer — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How does a lock-free ring buffer (the LMAX Disruptor's core idea) avoid
> locking entirely for a single-producer-single-consumer scenario, and why
> does that matter at high throughput?

Prerequisite: [`senior.md`](senior.md).

---

## The cost `middle.md`'s mutex-based approach pays

Every `put()`/`get()` in the condition-variable-based implementation
acquires a lock — under extremely high throughput (millions of items per
second), lock acquisition/release overhead itself (even uncontended,
per the Locking & Concurrency Control professional page's latch/lock
manager internals discussion) becomes a measurable cost, and any
contention between the producer and consumer threads adds real latency
variance.

## The lock-free ring buffer: pre-allocated, indexed by atomic counters

```mermaid
flowchart LR
    RingBuffer["Pre-allocated circular\narray (ring buffer)"] --> WriteIdx["Producer: atomic\nWRITE index"]
    RingBuffer --> ReadIdx["Consumer: atomic\nREAD index"]
    WriteIdx -.-.- ReadIdx
    Note["No lock at all - just\natomic increment/compare\noperations on two indices"]
```

For a **single**-producer-single-consumer scenario specifically, a ring
buffer backed by a pre-allocated fixed-size array and two atomic indices
(write position, read position) needs **no lock whatsoever**: the
producer writes to its current write index and atomically advances it;
the consumer reads from its current read index and atomically advances
it; the two never touch the same array slot at the same instant as long
as the write index never laps the read index (buffer-full condition,
checked via comparing the two atomic values). This is the exact same
lock-free, atomic-CAS-based approach from the Skip List professional
page's lock-free concurrent structures discussion, applied to this
specific, simpler SPSC (single-producer-single-consumer) case.

```python
# Conceptual sketch, not production code
class LockFreeRingBuffer:
    def __init__(self, size):
        self.buffer = [None] * size
        self.size = size
        self.write_idx = AtomicInt(0)
        self.read_idx = AtomicInt(0)

    def put(self, item):
        next_write = (self.write_idx.get() + 1) % self.size
        if next_write == self.read_idx.get():
            raise BufferFullError()  # or spin/retry
        self.buffer[self.write_idx.get()] = item
        self.write_idx.set(next_write)  # atomic publish
```

## The LMAX Disruptor: the production-grade realization of this idea

The **LMAX Disruptor** (referenced in the LSM-Tree professional page's
compaction case study for its mechanical-sympathy design) generalizes this
ring-buffer idea to support multiple producers and multiple consumers,
with cache-line padding to avoid false sharing (per the Locking &
Concurrency Control professional page's cache-line contention
discussion) and batching to amortize the cost of the remaining necessary
coordination — achieving microsecond-level producer-to-consumer handoff
latency specifically by avoiding both locks and garbage/allocation churn
in the hot path.

## Production checklist (staff-level)

1. **Use a lock-based bounded buffer (`middle.md`) as the default** for
   most producer-consumer scenarios — it's simpler, well-understood, and
   sufficient for the vast majority of real workloads.
2. **Reach for a lock-free ring buffer only after measuring that lock
   contention/acquisition overhead is a genuine, quantified bottleneck**
   at your actual throughput — this is real added implementation
   complexity that isn't justified by default.
3. **For genuinely extreme-throughput, single-producer-single-consumer
   scenarios, evaluate an existing, well-audited implementation (LMAX
   Disruptor, or a language-standard-library lock-free queue)** rather
   than hand-rolling atomic-index ring buffer logic — this is exactly the
   kind of subtle, hard-to-verify correctness surface recommended against
   hand-implementing elsewhere in this tree (see the Skip List
   professional page's identical recommendation).
4. **Pad shared atomic counters to avoid false sharing** if implementing
   or configuring a lock-free structure — cache-line contention between
   the write and read index counters can silently degrade performance
   even with a correct lock-free algorithm.
5. **In a performance review for a high-throughput internal messaging
   need, measure actual lock-based throughput first** before assuming
   lock-free is necessary — many workloads that feel "high throughput"
   are well within a well-tuned lock-based bounded buffer's capability.

## Cheat Sheet

```text
+------------------------------------------------------------------+
|              PRODUCER-CONSUMER — INTERNALS & SCALE                   |
+------------------------------------------------------------------+
| Lock-based bounded buffer (mutex + condition variable): correct,      |
| simple default for most producer-consumer scenarios                   |
+------------------------------------------------------------------+
| Lock-free ring buffer (SPSC): pre-allocated array + two ATOMIC         |
| indices (write, read) - NO lock at all, producer/consumer never       |
| touch the same slot simultaneously as long as write doesn't lap read  |
| Same lock-free-via-atomics principle as skip lists, applied to this   |
| simpler single-producer/single-consumer case                          |
+------------------------------------------------------------------+
| LMAX Disruptor: production-grade generalization to multiple            |
| producers/consumers, with cache-line padding (avoid false sharing)     |
| and batching - achieves microsecond-level handoff latency              |
+------------------------------------------------------------------+
| Default to lock-based; reach for lock-free only after MEASURING a     |
| genuine, quantified bottleneck - use an existing audited              |
| implementation, don't hand-roll                                        |
+------------------------------------------------------------------+
```

## Test yourself

1. Why does a single-producer-single-consumer ring buffer need no lock at
   all, while a multi-producer or multi-consumer scenario would?
2. Why does the LMAX Disruptor pad its atomic counters to separate cache
   lines, and what problem does this prevent?
3. Design a decision process for when a team should consider moving from
   a lock-based bounded buffer to a lock-free ring buffer implementation.

## Further Reading

- Martin Thompson et al. — "Disruptor: High Performance Alternative to
  Bounded Queues for Exchanging Data Between Concurrent Threads" (the
  original LMAX Disruptor technical paper).
- See also: [Skip List — professional](../../../../databases/performance/14-indexing%20%26%20filtering/skip-list/professional.md),
  [Locking & Concurrency Control — professional](../../../../databases/transaction/locking-and-concurrency-control/professional.md).
