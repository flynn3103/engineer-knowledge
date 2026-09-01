# Code Comments & Docstrings — Junior

## Outcome

Build reliable habits in a small, known area. By the end, you can apply this topic in a way that another engineer can trust and act on.

## Core idea

Explain the non-obvious why and the callable contract; let readable code explain routine mechanics.

## At this level

Use the checklist below with a reviewer or existing example.

## Practical workflow

1. Identify the reader, their task, and the decision they must make.
2. Write the minimum accurate information that unblocks that task.
3. Link to the authoritative source instead of duplicating volatile facts.
4. Ask a real reader to follow it; fix the first point of confusion.
5. Update, automate, archive, or delete the page when the system changes.

## What good looks like

- A reader can find the answer quickly and knows its scope.
- Facts have an owner or an observable source of truth.
- Examples use realistic names, safe defaults, and expected outcomes.
- The page names risks, limits, and the next escalation path when relevant.

## Topic focus

Document public behavior, inputs, outputs, exceptions, side effects, and important invariants.

Do not restate names, document temporary implementation details, or let comments drift from behavior.

## Python example

```python
def charge(amount_cents: int, account_id: str) -> str:
    """Charge an active account and return the payment ID.

    Raises ValueError when the amount is not positive or the account is inactive.
    """
    if amount_cents <= 0:
        raise ValueError("amount_cents must be positive")
    return payment_gateway.charge(account_id, amount_cents)
```

The docstring explains the caller's contract; the function name and code explain the mechanics.

## Review checklist

- Is the purpose clear in the first few lines?
- Is each instruction current, specific, and safe to perform?
- Are assumptions, permissions, and failure cases visible?
- Can a link, example, or command be verified?
- Is there a named owner or a clear maintenance trigger?

## Practice

Make one focused update and ask a teammate whether they can use it without verbal help.

## Remember

Documentation succeeds when it reduces uncertainty at the moment someone needs to act.
