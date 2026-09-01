# Shared Memory - Senior

Correct locks can still collapse throughput. Measure lock wait time, hold time, queue depth, context switches, and cross-socket traffic before changing the design.

```mermaid
flowchart LR
    Hot[One hot lock] --> Shard[Shard state by key]
    Shard --> Local[Update locally]
    Local --> Merge[Merge at a checkpoint]
```

| Risk | Production symptom | Safer action |
|---|---|---|
| Coarse lock | low CPU, high wait | shorten or shard the critical section |
| Fine locks | deadlock | define and test one lock order |
| False sharing | high CPU, poor scaling | pad or separate hot counters |
| NUMA access | latency rises by socket | pin workers and keep state local |
| Unsafe reclamation | rare crash | use epochs, hazards, or a lock |

For Spark/Flink native extensions, test on the target CPU architecture; x86 success does not prove ARM correctness. Prefer immutable snapshots for readers and bounded queues for ownership transfer. Roll out with a mutex baseline and compare p99 latency, not only throughput.

Continue to [`professional.md`](professional.md).

## Test yourself

1. How can a correct mutex cause a throughput plateau?
2. Which metrics distinguish contention from slow I/O?
3. What proof is needed before replacing a lock with atomics?
