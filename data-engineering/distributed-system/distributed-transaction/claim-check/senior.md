# Claim-Check Pattern - Senior

Claim-check shifts pressure from the broker to object storage and creates cross-system lifecycle state.

| Failure | Control |
|---|---|
| uploaded, not published | delayed orphan reaper |
| published, upload unavailable | retry and quarantine |
| corrupted payload | hash rejection |
| slow replay after deletion | retention safety window |
| unauthorized URI | scoped identity and bucket policy |

Monitor orphan bytes, object fetch p99, hash failures, reference age, missing objects, and egress cost. Version metadata and encryption information so old consumers can replay retained references.

## Test yourself

1. What prevents the reaper racing a producer?
2. How does replay affect retention?
3. Which failures should enter a DLQ?

Continue to [`professional.md`](professional.md).
