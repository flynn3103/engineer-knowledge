# Functional Requirements — Middle

Compose individual requirements into coherent features. Identify dependencies, conflicts, and overlaps. Evaluate trade-offs: a feature that is easy to implement but creates maintenance burden or breaks existing workflows is a poor choice.

## The mental model

Requirements exist in a system. A single user action may trigger multiple requirements across different components. A feature is a cohesive set of requirements that delivers value to a user or business goal.

Evaluate:
- **Scope:** Does this feature fit within the current system boundary?
- **Dependencies:** What other features or systems must exist first?
- **Conflicts:** Does this requirement contradict or complicate existing behavior?
- **Testability:** Can you verify this feature end-to-end?
- **Maintenance:** Will this feature create ongoing support burden?

## Composing features

1. Group related requirements by user goal or workflow.
2. Identify preconditions and dependencies.
3. Map data flow: what information moves between components?
4. Define boundaries: what is in scope, what is not?
5. Write acceptance criteria at the feature level (end-to-end scenarios).

## Realistic scenario: Payment processing

**User goal:** Customer completes a purchase.

**Related requirements:**
- User selects items and adds to cart
- User enters shipping address
- User selects payment method
- System validates payment
- System creates order
- System sends confirmation email

**Dependencies:**
- Payment gateway integration must exist
- Email service must be available
- Inventory system must track stock

**Conflicts to resolve:**
- What if payment succeeds but email fails? (Retry policy needed)
- What if inventory changes between selection and checkout? (Reservation strategy needed)

**Feature-level acceptance criteria:**
- User completes checkout with valid payment → order created, confirmation email sent
- Payment fails → user sees error, cart preserved, can retry
- Inventory insufficient → user notified before payment attempt
- Email service down → order created, email retried asynchronously

## Under-application and over-application

**Under-application:** Writing only happy-path requirements. You miss error handling, edge cases, and integration points.

**Over-application:** Writing requirements for implementation details. "The system shall use Redis for caching" is not a functional requirement; "The system shall respond to repeated queries within 100 ms" is.

## Incremental adoption

Start with core workflows. Identify which requirements are essential for MVP and which can be deferred. Use feature flags to separate requirement implementation from deployment.

## Verification at multiple levels

1. **Unit level:** Individual requirement acceptance criteria pass.
2. **Feature level:** End-to-end workflow succeeds with realistic data.
3. **Integration level:** Feature works with dependent systems (payment gateway, email, inventory).

## Test yourself

1. How do you identify when a requirement is part of a feature vs. a separate feature?
2. What dependencies should you map before implementing a feature?
3. How do you handle conflicting requirements?
4. Why is end-to-end testing important for features?

Continue to [`senior.md`](senior.md).
