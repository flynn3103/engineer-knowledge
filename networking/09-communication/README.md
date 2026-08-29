# Communication

> Choose an interaction style from delivery, ordering, latency, compatibility, and failure requirements.

## Topics

| # | Topic | Practice outcome |
|---|---|---|
| 01 | [HTTP](01-http/junior.md) | Build and inspect a complete request and response. |
| 02 | [TCP](02-tcp/junior.md) | Recognize connection and byte-stream behavior. |
| 03 | [UDP](03-udp/junior.md) | Handle loss, duplication, and ordering explicitly. |
| 04 | [RPC](04-rpc/junior.md) | Define timeouts and failures across a remote call. |
| 05 | [gRPC](05-grpc/junior.md) | Evolve protobuf contracts and streaming calls. |
| 06 | [REST](06-rest/junior.md) | Model resources, methods, and status behavior. |
| 07 | [GraphQL](07-graphql/junior.md) | Bound query cost and schema evolution. |
| 08 | [Idempotent Operations](08-idempotent-operations/junior.md) | Make retries safe and observable. |

## Practice loop

Write the interaction contract, force a timeout after the receiver starts work, retry once, and verify whether the final state is correct.
