# Application Layer

> Shape service boundaries so ordinary changes remain local and partial failures remain recoverable.

## Topics

| # | Topic | Practice outcome |
|---|---|---|
| 01 | [Microservices](microservices/junior.md) | Identify when a network boundary earns its cost. |
| 02 | [Monolith vs Microservices](monolith-vs-microservices/junior.md) | Compare options from change and ownership evidence. |
| 03 | [Service Discovery](service-discovery/junior.md) | Register, resolve, and remove instances safely. |
| 04 | [API Composition](api-composition/junior.md) | Bound fan-out latency and partial results. |
| 05 | [Stateless Design](stateless-design/junior.md) | Move durable state to an explicit owner. |
| 06 | [Service Mesh Introduction](service-mesh-intro/junior.md) | Separate traffic policy from business logic deliberately. |
| 07 | [Serverless and FaaS](serverless-faas/junior.md) | Match execution limits to workload shape. |
| 08 | [Peer-to-Peer Architecture](peer-to-peer-architecture/junior.md) | Reason about discovery, trust, and inconsistent peers. |

## Practice loop

Trace one user operation across every service boundary, name the owner of each timeout and retry, and remove any boundary whose operational cost has no evidence-backed benefit.
