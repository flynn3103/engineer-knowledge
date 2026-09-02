# Communication

> Evolve API contracts, deliver real-time updates, and route traffic to the right target — while old and new consumers run at the same time.

This section covers how services and clients talk to each other, end to end: the API contracts they agree on, how updates reach a client in real time, and how traffic actually gets routed and delivered once a request leaves the client. The transport and network layer underneath all of this — TCP/IP, TLS, HTTP evolution, VPCs — lives in [Infrastructure → Network](../../infrastructure/network/README.md).

## API contracts and evolution

| # | Topic | Practice outcome |
|---|---|---|
| 01 | [API Gateway](api-gateway/junior.md) | Centralize edge policy without centralizing domain logic. |
| 02 | [REST Design at Scale](rest-design-at-scale/junior.md) | Keep resource contracts predictable under growth. |
| 03 | [GraphQL Federation](graphql-federation/junior.md) | Define schema ownership and composition checks. |
| 04 | [gRPC and Streaming](grpc-and-streaming/junior.md) | Operate long-lived and backpressured streams. |
| 05 | [Versioning and Deprecation](versioning-and-deprecation/junior.md) | Migrate consumers with measurable exit conditions. |
| 06 | [Pagination and Filtering](pagination-and-filtering/junior.md) | Preserve stable traversal under changing data. |
| 07 | [Idempotency and Retries](idempotency-and-retries/junior.md) | Prevent duplicate effects across failures. |
| 08 | [Webhooks](webhooks/junior.md) | Deliver signed events with retry and replay controls. |
| 09 | [Backends for Frontends](backends-for-frontend/junior.md) | Give client experiences focused composition boundaries. |

## Real-time and long-lived connections

| # | Topic | Practice outcome |
|---|---|---|
| 10 | [WebSockets](websockets/junior.md) | Operate a bidirectional connection safely. |
| 11 | [Long Polling and Streaming](long-polling-and-streaming/junior.md) | Match delivery style to update behavior. |

## Traffic routing and delivery

Each of these is a topic cluster with its own set of subtopics — open the cluster's README for the full breakdown.

| # | Cluster | Focus |
|---|---|---|
| 12 | [Load Balancers](load-balancers/README.md) | Route traffic only to capable targets and prove failure detection and recovery behave as designed — 7 subtopics from L4/L7 routing to global server load balancing. |
| 13 | [Content Delivery Networks](content-delivery-networks/README.md) | Control which responses are cached, where they're served, and how stale or unsafe content is removed — 5 subtopics from pull/push CDN to cache invalidation. |
| 14 | [Domain Name System](domain-name-system/README.md) | Resolve a name deliberately, predict cache behavior, and roll out record changes without guessing — 5 subtopics from resolution flow to GeoDNS/anycast. |

## Practice loop

Choose one contract change, list every active consumer, deploy a compatible intermediate state, and define the telemetry that proves the old contract can be removed. For the routing and delivery clusters, use each cluster's own practice loop — the loop differs by what you're actually changing (a cache key, a health check, a DNS record).
