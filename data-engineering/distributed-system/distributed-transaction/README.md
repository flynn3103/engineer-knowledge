# Distributed Transaction

> Covers 2PC 3PC Coordinator, Claim Check, Distributed Lock With Fencing, Fan Out Fan In Pipeline, Saga Orchestration vs Choreography, Scatter Gather Aggregator, and TCC Try Confirm Cancel.

## Topics

| Topic | What it covers |
|---|---|
| [2PC 3PC Coordinator](2pc-3pc-coordinator/) | Atomic commit gives several participants one durable decision, at the cost of coordination and blocking. |
| [Claim Check](claim-check/) | Keep large payloads in object storage and send a small, verifiable reference through the broker. |
| [Distributed Lock With Fencing](distributed-lock-with-fencing/) | A lease coordinates current ownership; a fencing token lets the resource reject stale owners. |
| [Fan Out Fan In Pipeline](fan-out-fan-in-pipeline/) | Process independent items concurrently, then merge their results with bounded resources. |
| [Saga Orchestration vs Choreography](saga-orchestration-vs-choreography/) | A Saga coordinates local commits and explicit compensations without pretending they are one database transaction. |
| [Scatter Gather Aggregator](scatter-gather-aggregator/) | Query independent branches in parallel and combine enough answers under one deadline. |
| [TCC Try Confirm Cancel](tcc-try-confirm-cancel/) | Reserve resources first, then durably confirm or cancel every reservation. |
