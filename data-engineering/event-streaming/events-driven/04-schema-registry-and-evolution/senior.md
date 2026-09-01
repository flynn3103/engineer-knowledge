# Schema Evolution - Senior
| Mistake | Result | Better approach |
|---|---|---|
| remove required field | old-reader failure | deprecate, observe, then remove |
| reuse field meaning | silent corruption | create a new field |
| registry outage on hot path | consumer outage | bounded schema cache |
| latest-only test | replay failure | transitive history test |
| unbounded quarantine | hidden data loss | alert and governed replay |
Track incompatible submissions, unknown IDs, deserialize failures, schema-cache misses, and consumer-version distribution.
## Test yourself
1. Why is semantic compatibility harder than syntax?
2. How can caching survive registry outage?
3. What proves a field is safe to remove?
Continue to [`professional.md`](professional.md).
