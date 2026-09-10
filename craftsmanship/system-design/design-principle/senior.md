# High-Level Design — Senior

Manage system boundaries and ownership. Define which team owns which component. Set invariants: what must always be true? Handle failure modes: what happens when a component fails, is slow, or behaves unexpectedly?

## The mental model

A system is not just components and interfaces. It is a set of:
- **Boundaries:** What is inside the system? What is outside?
- **Ownership:** Which team owns which component?
- **Invariants:** What must always be true? (e.g., "orders are never lost")
- **Failure modes:** What can go wrong? How do we recover?

## System boundaries

Define what is in scope:
- **Core system:** Components you own and operate
- **Dependencies:** External systems you rely on (payment gateway, email service)
- **Integrations:** How external systems connect to you

Example:
- **Core:** Order Service, Inventory Service, Notification Service
- **Dependencies:** Payment Gateway (Stripe), Email Service (SendGrid)
- **Integrations:** Mobile app, web app, third-party sellers

## Ownership and accountability

Assign ownership:
- **Order Service:** Owned by Order Team. Responsible for order creation, updates, cancellation.
- **Inventory Service:** Owned by Inventory Team. Responsible for stock tracking, reservations.
- **Payment Service:** Owned by Payments Team. Responsible for payment processing, refunds.

Clear ownership means:
- One team is accountable for each component
- Changes require coordination with the owner
- On-call rotation is clear

## Invariants and contracts

Define invariants: properties that must always be true.

Examples:
- "An order is never lost" → Orders are persisted before payment is attempted
- "Inventory is never oversold" → Stock is reserved before payment
- "Payments are never duplicated" → Idempotent payment requests

Define contracts between components:
- Order Service → Payment Service: "I will send a payment request with a unique idempotency key"
- Payment Service → Order Service: "I will return success or failure, never partial success"

## Failure modes and recovery

Identify what can go wrong:

| Failure | Impact | Recovery |
|---|---|---|
| Payment Service down | Orders cannot be created | Queue payment requests, retry when service recovers |
| Inventory Service slow | Order creation is slow | Cache inventory, accept eventual consistency |
| Email Service fails | User doesn't get confirmation | Retry asynchronously, log for manual follow-up |
| Network partition | Services cannot communicate | Use circuit breaker, fail gracefully |

## Realistic scenario: Multi-region e-commerce

**System boundaries:**
- **Core:** Order Service, Inventory Service, User Service
- **Regional:** Payment Service (per region), Fulfillment Service (per region)
- **External:** Payment Gateway, Shipping Provider, Email Service

**Ownership:**
- Order Team: Order Service (global)
- Inventory Team: Inventory Service (global)
- Payments Team: Payment Service (per region)
- Fulfillment Team: Fulfillment Service (per region)

**Invariants:**
- "Orders are never lost" → Persisted before payment
- "Inventory is accurate" → Reserved before payment, released on cancellation
- "Payments are idempotent" → Same request always produces same result

**Failure modes:**
- Regional Payment Service down → Use fallback region or queue for retry
- Inventory Service slow → Cache recent inventory, accept eventual consistency
- Shipping Provider API down → Queue fulfillment requests, retry when available

## Evolution and compatibility

As the system grows, components may need to change:
- **Backward compatibility:** New versions of a component must work with old versions of callers
- **Deprecation:** Old interfaces are marked as deprecated, callers have time to migrate
- **Feature flags:** New behavior is hidden behind flags, can be rolled back

## Questions that expose weak assumptions

1. What happens if this component fails?
2. Which team owns this component? Are they on-call?
3. What invariants must this component maintain?
4. How do we know if this component is working correctly?
5. What is the cost of changing this component?

## Test yourself

1. How do you define system boundaries?
2. What is an invariant and why is it important?
3. How do you handle a failure in a critical component?
4. What makes a component "owned" by a team?

Continue to [`professional.md`](professional.md).
