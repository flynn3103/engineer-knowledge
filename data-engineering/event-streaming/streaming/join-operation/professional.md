# Streaming Join Operations - Professional

> Streaming joins are state indexes plus time/version constraints and a changelog
> contract for results that may be revised.

## Named systems

**Apache Flink** interval joins buffer keyed records from both inputs and register
cleanup timers based on interval bounds and watermarks. Flink SQL regular joins
may retain unbounded state without time constraints; interval and temporal joins
provide bounded or version-aware alternatives. Dynamic tables emit insert,
update, and delete changelog rows that sinks must understand.

**Kafka Streams** implements KStream-KStream joins with window stores and grace
periods. KStream-KTable joins probe the current table state, while KTable-KTable
joins represent updates to changing relations. Repartition and changelog topics
make shuffle and state durability explicit. Join result timestamps and cache/
commit intervals affect downstream visibility.

**Apache Beam** commonly expresses joins through keyed `CoGroupByKey`, windows,
triggers, and state. Correctness follows Beam's pane and accumulation semantics;
portable code cannot assume that a runner materializes the join with a specific
hash-table implementation.

## Scale and failure behavior

Join state is approximately arrival rate times retention times retained bytes,
multiplied by skew and duplicate multiplicity. At 100k records/s per side, 30
minutes of retention, and 500 retained bytes per record, raw state approaches 180
GB before indexes, timers, replication, and storage-engine amplification.

At 10x key skew, one shard fails first despite adequate fleet capacity. At 100x
duplicate multiplicity, output and sink load can grow quadratically. Watermark
stalls retain both sides and can turn a latency incident into disk exhaustion.

Temporal joins depend on version retention. Compacting history too early makes
old events impossible to enrich correctly after replay. Keeping all versions
forever moves the unbounded-state problem into the reference table.

## Operations

Dashboard state bytes and records by side, unmatched age, join match rate,
output/input ratio, hot-key distribution, watermark skew, late-match/retraction
counts, timer count, spill/compaction, checkpoint size, and sink changelog errors.

Runbook for state growth: identify which side and keys grow; verify watermark
progress and join bounds; inspect duplicate multiplicity; sample unmatched ages;
confirm cleanup timers fire; throttle admission before changing retention, which
can silently alter correctness.

## Design and ops checklist

- Prove key uniqueness or quantify many-to-many multiplicity.
- Specify event-time bounds, grace, finality, and late-match handling.
- Choose latest-value versus temporal reference semantics explicitly.
- Ensure sinks consume append, upsert, or retract changelogs correctly.
- Estimate state with skew, indexes, timers, and storage amplification.
- Test watermark stalls, hot keys, replay, and reference-history compaction.
- Bound unmatched state and monitor the oldest retained record.
- Treat salting/replication as a semantic and capacity change.

```text
JOIN CHEAT SHEET
stream-stream   buffer both sides within a time bound
stream-table    probe current materialized value
temporal join   probe version valid at event time
outer join      final null may require waiting or retraction
state estimate  rate x retention x bytes x multiplicity
```

## Test yourself

1. Estimate state for two 50k/s streams retaining 20 minutes at 300 bytes each.
2. When does a KStream-KTable join fail replay determinism?
3. How would you detect output explosion before the sink collapses?
4. What must a sink support for early outer-join results?

## Further reading

- Apache Flink documentation, interval and temporal joins and dynamic tables.
- Kafka Streams developer guide, join semantics and window stores.
- Apache Beam Programming Guide, windowing and `CoGroupByKey`.
- Begoli et al., "One SQL to Rule Them All."
- Akidau et al., "The Dataflow Model."
