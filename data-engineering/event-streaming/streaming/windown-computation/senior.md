# Window Computation - Senior

> How do you make lateness, corrections, and state retention safe and explicit?

| Policy | Freshness | Completeness | State/output cost |
|---|---|---|---|
| Short watermark delay, drop late | high | lower | low |
| Allowed lateness with updates | medium | higher | corrections and retained state |
| Long delay, one final result | low | high | large state and delayed output |
| Side output late events | primary stays fast | auditable repair | second reconciliation path |

An idle Kafka partition can hold back a minimum-of-partitions watermark forever.
Configure idleness detection so partitions with no events stop blocking progress,
but understand the risk when an apparently idle partition resumes with old data.

Use deterministic result keys such as `(account_id, window_start, window_end)`.
If late events update an emitted result, the sink must upsert or retract; an
append-only sink otherwise contains multiple contradictory answers.

State retention must exceed the accepted lateness and recovery horizon. Keeping
every closed window forever turns lateness support into an unbounded state leak.
Measure dropped-late records by source and lateness distribution before changing
the watermark policy.

## Test yourself

1. Why can one idle partition stop event-time progress?
2. What sink behavior is required for late window updates?
3. How should observed lateness distributions influence retention?

Continue to [`professional.md`](professional.md).
