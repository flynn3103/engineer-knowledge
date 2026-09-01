# Bad Structure Anti-Patterns — Junior

> Code has bad structure when a small change is difficult to find, understand, test, or safely delete.

## Goal

Recognize five common shapes and avoid adding to them. Do not start a large cleanup without help; make the next change clearer and safer.

## The shapes

| Anti-pattern | Signal | First move |
|---|---|---|
| God object | One class handles unrelated jobs. | Split the new responsibility out. |
| Spaghetti code | You cannot follow the order of decisions. | Name steps and make flow linear. |
| Lava flow | Old code remains because nobody understands it. | Trace usage before changing it. |
| Boat anchor | Unused code exists “just in case.” | Delete it when version control can restore it. |
| Arrow code | Nested conditions push work far to the right. | Use guard clauses. |

## God object

A class that validates orders, charges cards, sends email, and renders reports has too many reasons to change. New work should go to a focused collaborator.

```python
class OrderService:
    def __init__(self, payments, mailer):
        self.payments = payments
        self.mailer = mailer

    def place(self, order):
        self.payments.charge(order.total)
        self.mailer.send_confirmation(order)
```

Ask: “Would the same person change every method in this class?” If not, the boundary is probably wrong.

## Spaghetti and arrow code

Prefer named, straight-line steps. Handle invalid or irrelevant input first.

```python
def publish(order):
    if order.cancelled:
        return
    if not order.paid:
        return
    notify_customer(order)
    record_audit_event(order)
```

Guard clauses are not a trick: they make the normal path visible. If the branches describe a real workflow, extract states or small functions instead of adding more flags.

## Lava flow and boat anchors

- Search for callers, routes, jobs, configuration, and generated references before declaring code unused.
- Add or keep a test that covers behavior you intend to preserve.
- Remove one unused path in a small change; let monitoring and version control provide the safety net.
- Do not keep commented-out implementations. Explain the decision in history, an issue, or a short document instead.

## Before you commit

- Can a reader name the job of each changed function or class?
- Did nesting get shallower, not deeper?
- Did you avoid adding a “temporary” unused branch or helper?
- Can you describe how the change is tested?

## Check your understanding

1. What is the difference between code you do not understand and code that is unused?
2. When is a guard clause clearer than another nested `if`?
3. Which responsibility in your current change could be separated today?
