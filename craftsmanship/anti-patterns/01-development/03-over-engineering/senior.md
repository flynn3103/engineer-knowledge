# Over-Engineering Anti-Patterns — Senior

> At system scale, excess complexity becomes an operating cost: more deploys, failure modes, coordination, onboarding, and incident time.

## Goal

Remove unjustified architecture safely while preserving customer behavior and changing the incentives that produced it.

## Find the force, not only the smell

- A team may copy a large company’s architecture without its scale problem.
- Promotions or visibility may reward additions more than deletion.
- Shared libraries and platforms may be easier to start than to govern.
- Decision makers may not carry the operational cost of their choices.

Name the force in the plan; otherwise the same complexity returns under a new name.

## Simplify through a controlled migration

1. State the customer outcome and the cost of the current design.
2. Map contracts, data ownership, runtime dependencies, and rollback constraints.
3. Add a compatibility seam and measure correctness, latency, and operational load.
4. Move one flow or consumer cohort at a time.
5. Remove old infrastructure, contracts, and runbooks when usage reaches zero.

```python
class PaymentsGateway:
    def charge(self, request):
        return self._legacy_charge(request)


class OrdersService:
    def __init__(self, payments):
        self.payments = payments

    def place(self, order):
        return self.payments.charge(order.payment_request())
```

The gateway lets a distributed dependency be replaced or merged without forcing every caller to change at once.

## Architecture-scale smells

| Local smell | System-scale form |
|---|---|
| One-use interface | Plugin platform or provider framework with one consumer. |
| Lasagna layers | Services that only serialize and forward a request. |
| Soft coding | Untyped rules engine that bypasses tests and review. |
| Premature optimization | Sharding, queues, or caches before load evidence exists. |
| Bikeshedding | Long technology debates with no decision criterion. |

## Leadership practices

- Require an explicit problem, alternatives, reversibility, and exit condition for major additions.
- Celebrate deletion, consolidation, and simpler operation as engineering outcomes.
- Keep teams close to the code and on-call consequences of their decisions.
- Fund simplification with the same rigor as new capability.

## Check your understanding

1. What evidence says a service or platform should exist separately?
2. What compatibility path makes the next deletion reversible?
3. Which incentive is sustaining unnecessary complexity?
