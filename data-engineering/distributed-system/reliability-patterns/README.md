# Reliability Patterns

> Covers Bulkhead, Circuit Breaker, Compensating Transaction, Deployment Stamps and Geodes, Distributed Tracing, Health Endpoint Monitoring, Leader Election, Queue Based Load Leveling, Redundancy and Failure Domains, Retry, Service Mesh, Shuffle Sharding, Throttling, and Vector Clock.

## Topics

| Topic | What it covers |
|---|---|
| [Bulkhead](bulkhead/) | Named after a ship's watertight compartments: partition resources (thread pools, connections, capacity) so that one failing or overloaded… |
| [Circuit Breaker](circuit-breaker/) | Stop calling a dependency that's clearly failing, instead of retrying it into the ground. A circuit breaker trips open after enough… |
| [Compensating Transaction](compensating-transaction/) | When a multi-step operation fails partway through, you can't roll back steps that already committed in independent systems — you can only… |
| [Deployment Stamps and Geodes](deployment-stamps-and-geodes/) | Instead of one giant, shared deployment serving every customer, deploy multiple independent, identical copies ("stamps") — each… |
| [Distributed Tracing](distributed-tracing/) | A single user request can fan out across dozens of services — distributed tracing stitches every hop back together into one coherent… |
| [Health Endpoint Monitoring](health-endpoint-monitoring/) | A `/health` endpoint sounds trivial — return 200 if you're up. Getting it right (liveness vs. readiness, avoiding false positives, not… |
| [Leader Election](leader-election/) | This is the same leader election covered in full technical depth at [Consensus: Leader… |
| [Queue Based Load Leveling](queue-based-load-leveling/) | Put a queue between a bursty producer and a fixed-capacity consumer, so the consumer processes at its own sustainable pace while the queue… |
| [Redundancy and Failure Domains](redundancy-and-failure-domains/) | Running two copies of something only helps if the thing that could take down the first copy can't also take down the second. A failure… |
| [Retry](retry/) | The general-purpose reliability pattern for transient faults — this page covers the pattern's classification and policy design; the deep… |
| [Service Mesh](service-mesh/) | Move cross-cutting network concerns — retries, circuit breaking, mTLS, observability — out of application code and into a dedicated… |
| [Shuffle Sharding](shuffle-sharding/) | A clever combinatorial trick: instead of assigning each customer to one shared shard (where a noisy neighbor on that shard affects everyone… |
| [Throttling](throttling/) | Deliberately limit how much traffic a client (or the system as a whole) can send, before an overload happens — the proactive counterpart to… |
| [Vector Clock](vector-clock/) | Wall clocks can't reliably tell you which of two events on different machines happened first — a vector clock uses per-node counters to… |
