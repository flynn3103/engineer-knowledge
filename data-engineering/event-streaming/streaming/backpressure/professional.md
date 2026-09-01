# Streaming Backpressure - Professional

> Backpressure is distributed flow control across scheduler, network, state, and
> external-service boundaries; one non-propagating edge defeats the design.

## Named implementations

**Apache Flink** uses credit-based network flow control. An input channel grants
credits corresponding to available exclusive/floating buffers; an upstream
subpartition sends only while it has credits. Task metrics expose busy, idle,
and backpressured time. Since FLIP-76, unaligned checkpoints can include in-flight
buffers to bypass long alignment under pressure.

**Reactive Streams** formalizes demand through `Subscriber.request(n)`. Operators
must not emit more than requested. Libraries such as Akka Streams and Reactor
propagate demand across fused and asynchronous boundaries, but adapters to
callback or queue APIs can break the contract if they buffer without bounds.

**Spark Structured Streaming** is micro-batch driven rather than continuously
credit-driven. Trigger scheduling and source admission, including Kafka
`maxOffsetsPerTrigger`, bound each batch. If processing time exceeds trigger
interval, batches queue logically and input lag grows. Continuous processing has
different semantics and narrower operator support.

## Scale and failure behavior

At 10x input rate, the first hard boundary is often sink quota, network buffers,
or a hot partition. At 100x backlog, recovery time becomes the constraint: a job
that catches up at only 1.2 times live rate needs five hours to clear one hour of
lag. Capacity planning must include catch-up headroom, not just steady state.

Large buffers improve burst tolerance but increase memory, GC work, checkpoint
size, and cancellation latency. Tiny buffers increase scheduling and network
overhead. Tune from burst distribution and bandwidth-delay product, then test
failure recovery with the selected values.

TCP flow control is insufficient. A process can eagerly drain sockets into an
unbounded application queue, keeping the TCP receive window open while its own
operators fail. Flow control must reach the semantic admission point.

## Operations

Dashboard per-subtask busy/backpressured/idle time, queue or buffer occupancy,
records and bytes per edge, source lag and lag derivative, watermark lag,
checkpoint alignment duration/bytes, sink latency, retries, and throttling.

Runbook: locate the first saturated downstream task; verify skew; separate sink
service time from queue time; inspect checkpoint alignment; throttle admission;
then increase the actual constrained resource or reduce work. Avoid blind
restarts, which discard useful queue evidence and add replay load.

## Design and ops checklist

- Ensure every graph edge has a bounded capacity or explicit drop policy.
- Verify pressure propagates through adapters and external client libraries.
- Keep durable backlog in the log rather than process memory.
- Capacity-plan for catch-up rate and maximum acceptable recovery time.
- Distinguish hot-key skew from fleet-wide saturation.
- Test aligned and unaligned checkpoint behavior under downstream stalls.
- Add hysteresis and cooldown to lag-driven autoscaling.
- Declare loss, sampling, and freshness policies as product semantics.

```text
BACKPRESSURE CHEAT SHEET
record flow       source -> operators -> sink
pressure flow     sink -> operators -> source
durable backlog   broker/log, not heap
Flink             credit-based network buffers
Reactive Streams  explicit request(n) demand
Spark             trigger/source admission bounds
```

## Test yourself

1. A job processes 120k/s against 100k/s live traffic. How long does it need to
   clear 360 million records of lag, assuming rates remain stable?
2. How would you prove a library adapter breaks end-to-end demand propagation?
3. When are unaligned checkpoints operationally preferable, and what grows?
4. Which signals distinguish sink throttling from hot-key skew?

## Further reading

- Apache Flink documentation, network buffers and backpressure monitoring.
- FLIP-76, "Unaligned Checkpoints."
- Reactive Streams specification, rules 1.1 through 3.17.
- Apache Spark Structured Streaming programming guide, input rate controls.
- Tyler Akidau et al., *Streaming Systems*.
