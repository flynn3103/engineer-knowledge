# High-Level Design — Professional

Evolve architecture with teams. Architecture is not static; it evolves as the business grows, teams scale, and technical constraints change. Decompose architecture into team-owned services. Track migration and manage technical debt.

## Design and operations checklist

1. **Align architecture with team structure.** Each team owns one or more services. Services have clear boundaries and contracts.
2. **Define service ownership and SLOs.** Who is on-call? What are the availability and latency targets?
3. **Plan for evolution.** Which components will need to scale? Which will need to change?
4. **Manage dependencies.** Which services depend on which? Can you deploy independently?
5. **Track technical debt.** Which components are legacy? Which need refactoring?
6. **Establish governance.** How do teams coordinate changes? How do you prevent breaking changes?

## Service-oriented architecture

Decompose the system into services:
- **Service:** A deployable unit owned by one team
- **Boundary:** Clear API, no direct database access from other services
- **Autonomy:** Can be deployed independently
- **Scalability:** Can be scaled independently

Example: E-commerce platform

```
API Gateway
    ↓
├─ User Service (User Team)
├─ Product Service (Product Team)
├─ Order Service (Order Team)
├─ Payment Service (Payments Team)
├─ Inventory Service (Inventory Team)
└─ Notification Service (Notifications Team)
```

Each service:
- Has its own database
- Exposes a REST or gRPC API
- Can be deployed independently
- Has its own on-call rotation

## Dependency management

Map service dependencies:

| Service | Depends On | Criticality | Fallback |
|---|---|---|---|
| Order Service | Payment Service, Inventory Service | Critical | Queue orders if dependencies down |
| Payment Service | Payment Gateway | Critical | Fail fast, retry later |
| Notification Service | Email Service | Non-critical | Retry asynchronously |

Minimize dependencies:
- Circular dependencies are problematic (A depends on B, B depends on A)
- Long dependency chains are fragile (A → B → C → D)
- External dependencies are risky (payment gateway, email service)

## Migration and technical debt

Track components that need refactoring:

| Component | Status | Plan | Owner | Timeline |
|---|---|---|---|---|
| Monolithic Order Service | Legacy | Split into Order + Fulfillment | Order Team | Q2-Q3 |
| Synchronous Payment Flow | Slow | Migrate to async | Payments Team | Q1-Q2 |
| Shared Database | Tight coupling | Migrate to service-owned databases | All teams | Q2-Q4 |

Incremental migration:
1. Run old and new systems in parallel
2. Route traffic gradually to new system
3. Monitor for issues
4. Decommission old system

## Governance and coordination

Establish processes:
- **API Review:** New APIs are reviewed for consistency and compatibility
- **Dependency Review:** New dependencies are reviewed for risk
- **Deployment Coordination:** Teams coordinate deployments to avoid cascading failures
- **Incident Response:** Clear escalation path when services fail

## Realistic scenario: Scaling from monolith to microservices

**Current state (Monolith):**
- Single codebase, single database
- All features in one service
- Deployed as one unit

**Problems:**
- Slow deployment (any change requires full regression testing)
- Tight coupling (changes in one feature break others)
- Scaling is inefficient (scale entire monolith, not individual features)
- Team coordination is difficult (all teams modify same codebase)

**Target state (Microservices):**
- User Service (User Team)
- Product Service (Product Team)
- Order Service (Order Team)
- Payment Service (Payments Team)
- Inventory Service (Inventory Team)

**Migration plan:**
- **Phase 1:** Extract User Service (low risk, few dependencies)
- **Phase 2:** Extract Product Service (medium risk, read-heavy)
- **Phase 3:** Extract Order Service (high risk, many dependencies)
- **Phase 4:** Extract Payment Service (critical, requires careful coordination)
- **Phase 5:** Extract Inventory Service (complex state management)

**Verification:**
- Each phase is deployed to production with feature flags
- Traffic is gradually shifted to new service
- Old service remains as fallback
- Metrics are monitored for regressions

## Metrics and observability

Track architecture health:
- **Deployment frequency:** How often can each service be deployed?
- **Lead time:** How long from code commit to production?
- **Mean time to recovery:** How long to recover from a failure?
- **Change failure rate:** What percentage of deployments cause incidents?

## Test yourself

1. How do you decide when to split a monolith into microservices?
2. What makes a good service boundary?
3. How do you handle dependencies between services?
4. What is the cost of a microservices architecture?

## Further reading

- Sam Newman, *Building Microservices*
- Tanya Reilly, *The Staff Engineer's Path*
- Google SRE, distributed systems and service architecture chapters
