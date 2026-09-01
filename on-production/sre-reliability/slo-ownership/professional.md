# SLO Ownership — Professional

<!-- level-focus -->
At professional level, focus on this question:

> Can you establish a durable ownership model across teams, vendors, and reorganizations without creating coordination overload?

---

## Durable accountability

Make ownership part of service lifecycle: creation requires an owner and support contract; transfer requires an acceptance review; retirement requires SLO and alert removal. Contracts define customer outcome, internal dependency limits, vendor escalation, and incident communication authority. Keep the registry discoverable and automate stale-owner checks.

## Organization scenario

Platform, commerce, and a payment vendor share an order promise. Commerce owns customer outcome and communication; platform owns shared ingress capacity; vendor management owns commercial escalation; payments owns adapter behavior. An incident commander can activate this map without negotiating responsibility in the outage.

## Measures and governance

Track stale ownership records, page-routing success, dependency-engagement time, and recurring handoff failures. Treat repeated cross-team coordination as a signal to simplify service boundaries or create a product-aligned platform interface.

## Apply it

1. Define ownership acceptance criteria for a service transfer.
2. Write a vendor dependency escalation contract.
3. Choose an audit signal for stale ownership.

## Verify your work

- A reorganization cannot leave an unowned live SLO.
- Vendor incidents have technical and business escalation routes.
- Ownership reviews improve response evidence over time.

## Review questions

- What lifecycle events must update ownership?
- Why do vendor dependencies need explicit contracts?
- How can coordination metrics guide architecture?
