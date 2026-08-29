# API Design at Scale

> Evolve contracts and traffic policies while old and new consumers run at the same time.

## Topics

| # | Topic | Practice outcome |
|---|---|---|
| 01 | [API Gateway](01-api-gateway/junior.md) | Centralize edge policy without centralizing domain logic. |
| 02 | [REST Design at Scale](02-rest-design-at-scale/junior.md) | Keep resource contracts predictable under growth. |
| 03 | [GraphQL Federation](03-graphql-federation/junior.md) | Define schema ownership and composition checks. |
| 04 | [gRPC and Streaming](04-grpc-and-streaming/junior.md) | Operate long-lived and backpressured streams. |
| 05 | [Versioning and Deprecation](05-versioning-and-deprecation/junior.md) | Migrate consumers with measurable exit conditions. |
| 06 | [Pagination and Filtering](06-pagination-and-filtering/junior.md) | Preserve stable traversal under changing data. |
| 07 | [Idempotency and Retries](07-idempotency-and-retries/junior.md) | Prevent duplicate effects across failures. |
| 08 | [Webhooks](08-webhooks/junior.md) | Deliver signed events with retry and replay controls. |
| 09 | [Backends for Frontends](09-backends-for-frontend/junior.md) | Give client experiences focused composition boundaries. |

## Practice loop

Choose one contract change, list every active consumer, deploy a compatible intermediate state, and define the telemetry that proves the old contract can be removed.
