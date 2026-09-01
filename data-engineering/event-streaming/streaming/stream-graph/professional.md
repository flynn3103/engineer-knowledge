# Stream Graph - Professional

> At scale, an operator graph is a distributed scheduling, data-exchange, state
> ownership, and recovery plan.

## How real systems execute graphs

**Apache Flink** converts a `StreamGraph` into a `JobGraph`, then an
`ExecutionGraph` containing parallel execution vertices. Operator chaining
reduces serialization and network buffers. Network exchanges use result
partitions and input gates; credit-based flow control limits how much data a
receiver permits an upstream channel to send. Key groups are the atomic unit of
keyed-state assignment and rescaling.

**Kafka Streams** builds a processor topology of source, processor, and sink
nodes. Topic partitions define task parallelism. Repartition topics materialize
shuffle edges, while changelog topics back state stores. Cooperative rebalancing
and warmup replicas reduce, but do not eliminate, state-movement disruption.

**Apache Beam** keeps the graph portable. A runner translates Beam's transforms
and `PCollection` edges into its own execution plan. Fusion can combine stages;
`Reshuffle` or runner decisions create materialization boundaries. The portability
layer separates semantics from execution, but performance debugging requires
inspecting the runner-specific physical graph.

## Scale and failure behavior

At 10x throughput, serialization, shuffle bytes, and sink batching usually
surface before graph-scheduler limits. At 100x state, checkpoint duration,
restore bandwidth, key skew, and metadata/control-plane load dominate. A graph
with 1,000 operators at parallelism 500 describes hundreds of thousands of task
instances; deployment, heartbeats, and metric cardinality become material.

Chaining trades isolation for efficiency. A CPU-heavy map chained to a source
can delay source polling and watermark emission. Breaking the chain adds queues,
serialization, and buffers but creates a separate scheduling and backpressure
boundary. Decide from profiles and failure isolation, not visual neatness.

Topology upgrades fail when state identity or serializer snapshots no longer
match. Test savepoint restore against production-sized state and both upgrade
and rollback binaries. A restore test over tiny state does not reveal object
store listing, download, deserialization, or key-group skew bottlenecks.

## Operations

Dashboard busy/backpressured/idle time per subtask, records and bytes per edge,
shuffle buffer usage, watermark alignment, checkpoint alignment and duration,
state bytes by operator, restore time, and per-subtask skew. Preserve the
physical execution graph with each deployment artifact.

Runbook for rising end-to-end lag:

1. Find the first downstream operator whose busy time saturates.
2. Inspect its inputs for skew and its outputs for backpressure.
3. Separate compute time from serialization, network, state access, and sink I/O.
4. Verify watermark lag is not merely making event-time output appear delayed.
5. Apply a bound or topology change, then validate checkpoint and restore cost.

## Design and ops checklist

- Mark every shuffle, broadcast, stateful, and external-commit edge.
- Give stateful operators stable identity and versioned state serializers.
- Plan maximum parallelism and key-group count for expected growth.
- Quantify skew by work and state, not only record count.
- Choose chaining from CPU profiles, isolation, and backpressure behavior.
- Load-test checkpoints, restore, rescaling, and rollback with realistic state.
- Bound topology/task cardinality and telemetry dimensions.
- Store logical and physical graph plans with release metadata.

```text
STREAM GRAPH CHEAT SHEET
logical node     user-visible transform
physical task    parallel runtime instance
chain            less overhead, less isolation
shuffle          serialization + network + new partition ownership
key group        Flink unit of keyed-state rescaling
repartition log  Kafka Streams shuffle/materialization boundary
```

## Test yourself

1. A job is 40% backpressured but every CPU is below 50%. How would you locate
   whether shuffle buffers, state I/O, or the sink is responsible?
2. When should two operators be deliberately unchained?
3. How would you migrate a stateful graph while preserving rollback?
4. What control-plane risks appear at hundreds of thousands of task instances?

## Further reading

- Apache Flink source: `StreamGraph`, `JobGraph`, and `ExecutionGraph` packages.
- Apache Flink documentation, network stack and task chaining.
- Kafka Streams architecture and processor topology documentation.
- Apache Beam Runner API and "Fusing transforms" documentation.
- Carbone et al., "Apache Flink: Stream and Batch Processing in a Single Engine."
