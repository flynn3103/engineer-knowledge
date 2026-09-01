# TCC: Try, Confirm, Cancel - Professional

TCC externalizes a resource manager's provisional state as a business protocol.

## Real systems

- Seata TCC registers branch transactions and drives user-defined Try/Confirm/Cancel handlers.
- Hmily and ByteTCC persist transaction context and recover phase two.
- Payment authorization/capture/void is a real reservation-style protocol, though provider semantics vary.
- Inventory holds use conditional writes and expiry indexes to isolate reserved capacity.

At scale, reservation rows, expiry scans, hot inventory keys, and phase-two backlog dominate. Dashboard unavailable reserved capacity, oldest reservation, redrive rate, transition conflicts, and reconciliation drift.

## Design and operations checklist

- Define every legal state transition.
- Make phase two idempotent and commutative with retries.
- Reconcile TTL cleanup with the durable global decision.
- Provide manual resolution for contradictory evidence.

```text
Try = provisional resource claim
Confirm/Cancel = irreversible terminal choice
```

## Test yourself

1. How would you prove Cancel-before-Try safety?
2. Where must the authoritative decision survive?
3. What capacity cost does a long Try window create?

## Further reading

- Seata TCC Mode documentation and source.
- Pat Helland, *Life Beyond Distributed Transactions*.
- Payment authorization lifecycle documentation from major processors.
