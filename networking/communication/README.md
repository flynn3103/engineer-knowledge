# Communication

> Choose an interaction style from delivery, ordering, latency, compatibility, and failure requirements.

## Topics

| # | Topic | Practice outcome |
|---|---|---|
| 01 | [HTTP](http/junior.md) | Build and inspect a complete request and response. |
| 02 | [TCP](tcp/junior.md) | Recognize connection and byte-stream behavior. |
| 03 | [UDP](udp/junior.md) | Handle loss, duplication, and ordering explicitly. |
| 04 | [RPC](rpc/junior.md) | Define timeouts and failures across a remote call. |
| 05 | [gRPC](grpc/junior.md) | Evolve protobuf contracts and streaming calls. |
| 06 | [REST](rest/junior.md) | Model resources, methods, and status behavior. |
| 07 | [GraphQL](graphql/junior.md) | Bound query cost and schema evolution. |
| 08 | [Idempotent Operations](idempotent-operations/junior.md) | Make retries safe and observable. |

## Practice loop

Write the interaction contract, force a timeout after the receiver starts work, retry once, and verify whether the final state is correct.
