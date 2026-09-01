# Tidy First — When and How — Junior

**Tidying** is a small structural change that preserves behavior: rename a confusing variable, extract a duplicate expression, or remove unreachable code. Do it before a behavior change only when it makes the next step clearer and is easy to verify.

## Keep two kinds of work separate

- **Structure change:** same behavior, clearer shape.
- **Behavior change:** users can observe something new or different.

Make and test them separately. If a test changes because a feature changed, that belongs with the behavior change, not the tidy.

```python
# Before
if order.total > 50 and order.country == "VN":
    ship_free(order)

# Tidy: name the decision; behavior stays the same
qualifies_for_free_shipping = order.total > 50 and order.country == "VN"
if qualifies_for_free_shipping:
    ship_free(order)
```

## A simple rule

Tidy first when all are true:

1. The cleanup makes the immediate change easier.
2. You can describe why behavior is unchanged.
3. Tests or a quick check can confirm it.
4. The cleanup is small enough to undo easily.

Otherwise, make the requested change first and leave a note for later. Do not turn a small task into a cleanup expedition.
