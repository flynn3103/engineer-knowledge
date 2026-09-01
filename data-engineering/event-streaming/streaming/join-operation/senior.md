# Streaming Join Operations - Senior

> How do you keep joins bounded and semantically stable under late data, skew,
> updates, and outer-join nulls?

| Failure mode | Consequence | Control |
|---|---|---|
| Hot join key | one task and state shard saturate | salt only with correct replication/merge |
| Late counterpart | missing or corrective match | grace period plus revision policy |
| Many-to-many key | output explosion | uniqueness/version constraints |
| Reference update | replay changes enrichment | temporal/versioned lookup |
| Outer join early null | later match contradicts output | delay finality or emit retraction |

Outer joins are especially subtle. Emitting `(order, null)` before the lateness
horizon closes gives low latency, but a later payment requires retracting or
updating that result. Waiting until finality avoids correction but delays every
unmatched output.

Skew mitigation can change semantics. Salting one side requires replicating the
other side across salts, multiplying state. Heavy-key isolation is safer when a
small known set dominates. Monitor output-to-input ratio; it reveals accidental
many-to-many joins that input throughput alone hides.

Define replay semantics for dimension enrichment. "Latest value at processing
time" is nondeterministic across replays; historical/versioned tables preserve
the value valid at the event's timestamp.

## Test yourself

1. Why can an early outer-join null require a later retraction?
2. What state cost accompanies salted joins?
3. Which metric reveals many-to-many output explosion?

Continue to [`professional.md`](professional.md).
