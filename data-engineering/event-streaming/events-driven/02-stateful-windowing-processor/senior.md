# Stateful Windowing - Senior
| Failure or mistake | Control |
|---|---|
| watermark too fast | lost/side-output late events |
| watermark too slow | delayed output and state growth |
| hot key | key splitting or two-stage aggregation |
| unbounded session | timeout and state TTL |
| non-idempotent sink | transactional or deduplicated commit |
Track watermark lag, late-event rate, state bytes/keys, checkpoint duration, restore time, and backpressure. Test idle partitions because one silent source can hold back a global watermark.
## Test yourself
1. How can an idle partition stop progress?
2. What bounds state growth?
3. How do corrected late results reach a sink safely?
Continue to [`professional.md`](professional.md).
