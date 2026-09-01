# DLQ and Retry - Senior
| Mistake | Control |
|---|---|
| retry every error | explicit classification |
| synchronized retries | exponential backoff with jitter |
| infinite attempts | budget and DLQ |
| blind replay | dry run, rate limit, idempotency |
| ignored DLQ | age/volume SLO and owner |
Monitor retry amplification, DLQ age, failure class, replay success, and dependency health. Circuit-break retry publication when the failing dependency cannot recover under load.
## Test yourself
1. What creates a retry storm?
2. How should replay be throttled?
3. When must key ordering override non-blocking retry?
Continue to [`professional.md`](professional.md).
