# Bad Structure Anti-Patterns — Middle

> Structural debt grows through reasonable local decisions. Catch the second or third repetition, before it becomes a rewrite.

## Goal

Make local design choices that preserve cohesion, readable flow, and safe deletion. Review for the direction of travel, not only today’s defect.

## Detect the slope

| Trigger | Likely result | Countermove |
|---|---|---|
| “It is related, put it here.” | God object | Check for a single reason to change. |
| One more special case | Arrow or spaghetti flow | Extract a policy, state, or named step. |
| Replacement added beside old behavior | Lava flow | Plan and verify deletion. |
| “We may need it.” | Boat anchor | Record the idea; do not ship unused code. |

## Refactor in small, proven moves

1. Characterize current behavior with tests, logs, or examples.
2. Extract one cohesive unit behind the existing interface.
3. Move one caller at a time.
4. Remove the old path only after searches and tests show it is unused.

```python
class InvoiceSender:
    def __init__(self, mailer):
        self.mailer = mailer

    def send(self, invoice):
        self.mailer.send(invoice.customer.email, invoice.render())


class OrderService:
    def __init__(self, invoice_sender):
        self.invoice_sender = invoice_sender

    def confirm(self, order):
        self.invoice_sender.send(order.invoice)
```

The extraction has a clear owner and can be tested without building all of `OrderService`.

## Make control flow explain itself

- Use a table or dictionary for stable value-to-action selection.
- Use small named functions for stages of a workflow.
- Use an explicit state model when conditions depend on prior transitions.
- Keep exceptional recovery near the operation that can fail.

```python
HANDLERS = {"paid": notify_customer, "cancelled": issue_refund}

def handle(order):
    handler = HANDLERS.get(order.status)
    if handler is not None:
        handler(order)
```

Do not replace every `if` with indirection. A simple choice is clearer when it remains simple.

## Review questions

- Does this change add an unrelated reason for a class to change?
- Is the new branch a business rule, or evidence of a missing model?
- Is old code being replaced, or merely bypassed?
- Can the author show callers and tests before deleting a path?

## Check your understanding

1. What evidence would let you safely remove suspected dead code?
2. When should duplicated logic remain duplicated?
3. How would you split a class whose methods use unrelated sets of fields?
