# Anti-Patterns — Senior

Senior engineers manage patterns that cross services, teams, and release paths.

Dependency magnets, shared databases, distributed monoliths, retry storms, unbounded queues, fragile test suites, and platform abstractions without owners all convert local convenience into system-wide coordination cost.

Use hotspot analysis: change frequency × defect rate × coordination cost × operational impact. Improve the highest-risk path with seams, characterization tests, strangler migration, expand-contract schemas, traffic shaping, and explicit rollback.

Add architecture fitness functions for rules that can be automated: forbidden dependencies, latency budgets, schema compatibility, dependency cycles, and ownership metadata. Ratchet violations downward rather than demanding an impossible one-time cleanup.

## Test yourself

1. How do you distinguish a distributed monolith from useful services?
2. Which hotspot deserves investment first?
3. What makes an architecture fitness function useful?
4. How does a ratchet avoid blocking all delivery?

Continue to [`professional.md`](professional.md).
