# Window Computation - Professional

> Window semantics are a contract among timestamp extraction, progress
> estimation, triggers, accumulation, state cleanup, and sink revision support.

## Named systems

**Apache Flink** assigns windows per key and stores window state in the configured
state backend. Event-time timers fire when the operator watermark passes their
timestamp. The operator watermark is constrained by input watermarks; idleness
and watermark alignment address stalled or excessively fast inputs. Allowed
lateness retains state after the first firing, and side outputs can capture data
arriving after cleanup.

**Apache Beam** separates windows, triggers, allowed lateness, and accumulation
modes. Triggers can fire early, on-time, and late panes. Discarding mode emits
new contributions; accumulating mode emits revised aggregates. Runner portability
depends on respecting these semantics rather than assuming one engine's defaults.

**Kafka Streams** advances stream time from observed record timestamps. Window
stores retain keyed records or aggregates; grace periods define how long
out-of-order records remain acceptable. Suppression can hold intermediate results
until a window closes, trading downstream simplicity for buffer/state pressure.

## Scale and failure behavior

Sliding windows amplify state and computation roughly with `size / slide`. A
24-hour window sliding every minute can place each event into 1,440 logical
windows unless the engine applies incremental optimization. Session merging adds
indexing and rewrite costs under heavily interleaved keys.

At 10x key cardinality, timer and metadata overhead may dominate payload state.
At 100x lateness horizon, retained windows inflate checkpoints and recovery time.
A watermark stuck behind one source produces apparently healthy ingestion with
no emitted results and continuously growing state.

Timestamp quality is a trust boundary. Clock skew, seconds-versus-milliseconds
bugs, or malicious future timestamps can advance progress or retain state
incorrectly. Validate ranges and quarantine impossible timestamps before they
influence watermarks.

## Operations

Dashboard input and operator watermarks, watermark skew by partition, window
state bytes, active windows/timers, early/on-time/late pane counts, dropped-late
rate, cleanup delay, and sink correction failures.

Runbook for missing output: compare processing progress with watermark progress;
find the minimum input partition; inspect idleness and malformed timestamps;
check trigger and allowed-lateness configuration; estimate retained state before
forcing a watermark jump that could finalize many windows at once.

## Design and ops checklist

- Define event timestamp authority and validation bounds.
- Specify watermark generation, idleness, alignment, and restart behavior.
- Quantify window amplification and per-key state before deployment.
- Define early, on-time, and late output semantics for consumers.
- Ensure sinks support revisions, retractions, or immutable pane identity.
- Set cleanup from lateness and recovery requirements, not guesswork.
- Test skewed partitions, future timestamps, long idleness, and replay.
- Monitor lateness distribution before tightening correctness policy.

```text
WINDOW CHEAT SHEET
event time       business occurrence time
watermark        estimate that event-time progress passed t
trigger          when a pane emits
allowed lateness how long closed-window state accepts updates
accumulation     replacement total or incremental pane
retention        hard bound on state lifetime
```

## Test yourself

1. Estimate logical window amplification for a six-hour window sliding every
   five minutes.
2. How can one future-dated event corrupt watermark behavior?
3. What sink contract supports accumulating late panes safely?
4. Which metrics distinguish source idleness from a broken trigger?

## Further reading

- Akidau et al., "The Dataflow Model."
- Akidau, Chernyak, and Lax, *Streaming Systems*.
- Apache Flink documentation, event time, watermarks, and windows.
- Apache Beam Programming Guide, windowing and triggers.
- Kafka Streams documentation, window stores, grace, and suppression.
