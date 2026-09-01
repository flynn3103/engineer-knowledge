# Events Driven

> Covers Broker Bake Off, CDC Pipeline, Consumer Autoscaling On Lag, DLQ and Retry Topology, Event Driven, Event Replay and Reprojection, Idempotent Inbox Outbox, Schema Registry and Evolution, and Stateful Windowing Processor.

## Topics

| Topic | What it covers |
|---|---|
| [Broker Bake Off](broker-bake-off/) | Choose a broker from workload semantics and measured failure behavior, not popularity. |
| [CDC Pipeline](cdc-pipeline/) | Turn committed database changes into an ordered event stream without polling. |
| [Consumer Autoscaling On Lag](consumer-autoscaling-on-lag/) | Scale consumers from backlog age and processing capacity, while respecting partition parallelism and rebalance cost. |
| [DLQ and Retry Topology](dlq-and-retry-topology/) | Retry transient failures without blocking healthy traffic, and quarantine permanent failures for controlled repair. |
| [Event Driven](event-driven/) | Trigger work in response to something happening, not on a fixed schedule. A file lands in storage, an order is placed, a message arrives —… |
| [Event Replay and Reprojection](event-replay-and-reprojection/) | Rebuild a derived view from an immutable event log without disrupting the live view. |
| [Idempotent Inbox Outbox](idempotent-inbox-outbox/) | Atomically record intended messages and deduplicate received messages across database-broker boundaries. |
| [Schema Registry and Evolution](schema-registry-and-evolution/) | Evolve event contracts without breaking mixed-version producers, consumers, or historical replay. |
| [Stateful Windowing Processor](stateful-windowing-processor/) | Group unbounded events by event time while handling late data and recoverable state. |
