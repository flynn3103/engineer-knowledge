# High-Level Design — Middle

Design component interactions: define interfaces, communication patterns, and data contracts. Evaluate trade-offs: synchronous vs. asynchronous, request-response vs. event-driven, tight coupling vs. loose coupling.

## The mental model

Components interact through interfaces. An interface defines:
- **What data** is exchanged (request/response schema, event format)
- **How** it is exchanged (HTTP, gRPC, message queue, database)
- **When** it happens (synchronous, asynchronous, scheduled)
- **Failure behavior** (what happens if the component is down?)

Tight coupling (direct calls) is simple but fragile. Loose coupling (message queues, events) is resilient but complex.

## Communication patterns

| Pattern | Example | Pros | Cons |
|---|---|---|---|
| Request-Response | HTTP, gRPC | Simple, immediate feedback | Tight coupling, blocking |
| Publish-Subscribe | Message queue, event bus | Loose coupling, scalable | Eventual consistency, debugging harder |
| Batch Processing | Scheduled jobs | Efficient for large data | Delayed results, complex error handling |
| Streaming | Kafka, Pub/Sub | Real-time, high throughput | Complex state management |

## Designing interfaces

1. **Define the contract:** What data does the caller send? What does the receiver return?
2. **Choose the protocol:** HTTP for web, gRPC for services, message queue for events.
3. **Handle errors:** What happens if the call fails? Retry? Fallback? Fail fast?
4. **Version the interface:** How do you evolve the interface without breaking callers?

## Realistic scenario: E-commerce order processing

**Components:**
- Web Server (handles user requests)
- Order Service (creates and manages orders)
- Payment Service (processes payments)
- Inventory Service (tracks stock)
- Email Service (sends notifications)

**Design decision: Synchronous vs. Asynchronous**

**Synchronous approach:**
```
User → Web Server → Order Service → Payment Service → Inventory Service → Email Service
```

Pros: Simple, immediate feedback
Cons: If any service is slow or down, the entire flow fails

**Asynchronous approach:**
```
User → Web Server → Order Service → Message Queue
                                        ↓
                                  Payment Service
                                        ↓
                                  Inventory Service
                                        ↓
                                  Email Service
```

Pros: Resilient, scalable
Cons: Eventual consistency, harder to debug

**Hybrid approach:**
```
User → Web Server → Order Service (sync) → Message Queue (async)
                                               ↓
                                         Payment Service
                                               ↓
                                         Email Service
```

Order is created immediately (sync), payment and email happen asynchronously.

## Coupling and cohesion

**Tight coupling:** Components depend directly on each other. Changes in one break others.

**Loose coupling:** Components communicate through well-defined interfaces. Changes are isolated.

**High cohesion:** Related functionality is grouped together. Unrelated functionality is separated.

Example:
- **Tight coupling:** Order Service directly calls Payment Service's internal database
- **Loose coupling:** Order Service sends a payment request to Payment Service's API

## Incremental adoption

Start with synchronous request-response. Add asynchronous patterns when you need:
- Resilience (services can fail independently)
- Scalability (decoupling load)
- Eventual consistency (acceptable for some operations)

## Verification at multiple levels

1. **Interface level:** Can you call the interface and get the expected response?
2. **Integration level:** Do components work together correctly?
3. **Failure level:** What happens when a component is slow or down?

## Test yourself

1. When should you use synchronous vs. asynchronous communication?
2. How do you version an interface without breaking callers?
3. What is the difference between tight and loose coupling?
4. How do you handle failures in a distributed system?

Continue to [`senior.md`](senior.md).
