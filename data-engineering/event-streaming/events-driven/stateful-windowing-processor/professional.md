# Stateful Windowing - Professional
Flink uses keyed state backends, barrier-based checkpoints, and RocksDB/ForSt for state beyond heap. Kafka Streams uses local RocksDB stores backed by changelog topics.
Scale fails first through skew, state compaction, checkpoint I/O, and recovery bandwidth. Dashboard watermark alignment, busy/backpressured time, checkpoint p99, state growth, changelog lag, and restore ETA.
## Best practices
- Partition by a stable key and measure skew.
- Set explicit lateness, TTL, and correction semantics.
- Separate durable checkpoints from temporary local state.
- Capacity-plan full restore under degraded bandwidth.
```text
correct window = time semantics + watermark + late-data policy
recoverable window = state snapshot + replay position
```
## Test yourself
1. How would you restore 10 TB of keyed state inside an RTO?
2. What consistency must a sink provide with checkpoints?
3. When should state be repartitioned?
## Further reading
- Flink papers and checkpointing documentation.
- Kafka Streams state-store documentation.
- Akidau et al., *The Dataflow Model*.
