# Application Layer

> Shape service boundaries so ordinary changes remain local and partial failures remain recoverable.

## Topics

| # | Topic | Practice outcome |
|---|---|---|
| 01 | [Microservices](01-microservices/junior.md) | Identify when a network boundary earns its cost. |
| 02 | [Monolith vs Microservices](02-monolith-vs-microservices/junior.md) | Compare options from change and ownership evidence. |
| 03 | [Service Discovery](03-service-discovery/junior.md) | Register, resolve, and remove instances safely. |
| 04 | [API Composition](04-api-composition/junior.md) | Bound fan-out latency and partial results. |
| 05 | [Stateless Design](05-stateless-design/junior.md) | Move durable state to an explicit owner. |
| 06 | [Service Mesh Introduction](06-service-mesh-intro/junior.md) | Separate traffic policy from business logic deliberately. |
| 07 | [Serverless and FaaS](07-serverless-faas/junior.md) | Match execution limits to workload shape. |
| 08 | [Peer-to-Peer Architecture](08-peer-to-peer-architecture/junior.md) | Reason about discovery, trust, and inconsistent peers. |

## Practice loop

Trace one user operation across every service boundary, name the owner of each timeout and retry, and remove any boundary whose operational cost has no evidence-backed benefit.
