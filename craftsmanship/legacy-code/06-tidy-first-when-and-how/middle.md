# Tidy First — When and How — Middle

Tidy First is a sequencing discipline: make small, behavior-preserving structural moves before or after a behavior change, never mixed into the same reasoning step.

## Useful tidyings

- Give a concept a name with an explaining variable or function.
- Replace nested conditionals with guard clauses.
- Extract duplicated calculations.
- Move related code together.
- Delete code proven unreachable.
- Split a long function at a stable responsibility boundary.

```python
def eligible(order) -> bool:
    if order.cancelled:
        return False
    if not order.items:
        return False
    return order.total >= 50
```

This guard-clause tidy preserves the original decisions while making each one easier to inspect.

## Workflow

1. State the behavior change in one sentence.
2. List the structural obstacles to making it safely.
3. Make one tidy at a time; run tests after each.
4. Commit or clearly separate the tidy from the behavior change.
5. Stop tidying once the next behavior change is simple.

Avoid tidies that require guessing intent. Characterize first, or defer them. “Cleaner” is not evidence that behavior stayed the same.
