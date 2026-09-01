# Stateful Computation - Junior

> Why can a running total not be computed from the current event alone?

A stateless map converts each Debezium record independently. A running customer
balance, duplicate detector, or session needs facts from earlier records.

```mermaid
sequenceDiagram
    participant E as Events
    participant O as Operator
    participant S as Memory map
    E->>O: account A, +10
    O->>S: A = 10
    E->>O: account A, +7
    O->>S: read 10, write 17
    Note over S: process crashes; map disappears
```

The naive fix is an in-process dictionary. It is fast, but a crash loses it, a
second worker may own a conflicting copy, and millions of inactive keys remain
forever. Calling a warehouse for every event preserves data but adds network
latency, cost, and a new availability dependency to the hot path.

Stream processors instead manage state with partition ownership and checkpoint
recovery. Before using that mechanism, identify whether the state is a scalar,
map, list, recent-event buffer, or timer and when it is no longer needed.

## Test yourself

1. Why is a running total stateful?
2. What fails when two workers maintain the same key independently?
3. Why is a warehouse lookup per event usually a poor hot-path design?

Continue to [`middle.md`](middle.md).
