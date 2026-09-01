# Streaming Backpressure - Senior

> How do skew, checkpoints, and external sinks complicate an otherwise correct
> bounded-flow design?

Backpressure protects memory but increases latency. It can also delay checkpoint
barriers behind queued records. Under aligned Flink checkpoints, a fast input may
be paused while waiting for a barrier from a slow input, increasing buffered
alignment data and checkpoint duration.

| Failure mode | Evidence | Safer response |
|---|---|---|
| Hot key | one operator subtask backpressures | split associative aggregation |
| Slow sink API | high request latency and busy time | batch, bound, negotiate quota |
| Checkpoint alignment | alignment time and bytes rise | fix skew; consider unaligned checkpoints |
| GC feedback loop | buffers grow, pauses lengthen | reduce buffers and object churn |
| Autoscaling oscillation | repeated rescale and recovery | hysteresis, cooldown, lag derivative |

Unaligned checkpoints can snapshot in-flight network buffers instead of waiting
for channels to align. They reduce checkpoint completion time during pressure,
but enlarge checkpoint state and move network backlog into recovery artifacts.
They are not a substitute for fixing sustained capacity deficits.

Design overload policy explicitly. For lossless jobs, slow source consumption
and let durable lag grow within a recovery SLO. For freshness-first telemetry,
sampling or dropping may be valid, but must be measured and declared. Do not let
an accidental queue limit choose business semantics.

## Test yourself

1. Why can backpressure increase aligned-checkpoint duration?
2. What cost do unaligned checkpoints trade for faster completion?
3. How would you prevent lag-based autoscaling from oscillating?

Continue to [`professional.md`](professional.md).
