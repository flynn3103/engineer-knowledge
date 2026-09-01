# Fan-Out/Fan-In Pipeline - Professional

Pipeline design couples scheduling, queueing, ownership, backpressure, and failure propagation.

## Real systems

- Go `errgroup` couples child lifetimes and first-error cancellation.
- Java ForkJoinPool uses work stealing for recursive parallel work.
- Tokio task sets and semaphores bound asynchronous fan-out.
- Reactive Streams standardizes demand signaling between stages.

At 10x load queues hide pressure; at 100x they become the memory outage. Dashboard queue age, active workers, blocked duration, cancellation latency, and useful throughput. Runbooks must pause intake before draining stages.

## Design and operations checklist

- Set one end-to-end concurrency and memory budget.
- Define ownership, close, cancellation, order, and error contracts.
- Make pressure flow upstream.
- Test sink stalls and partial startup.

```text
bounded work + bounded queues + bounded lifetime
```

## Test yourself

1. How would you allocate capacity across unequal stages?
2. Which signal distinguishes CPU saturation from backpressure?
3. When does work stealing hurt locality?

## Further reading

- Reactive Streams specification.
- Go `x/sync/errgroup` source.
- Blumofe and Leiserson, *Scheduling Multithreaded Computations by Work Stealing*.
