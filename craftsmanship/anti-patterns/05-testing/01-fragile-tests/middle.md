# Fragile Tests — Middle

> **Focus:** tests coupled to incidental structure instead of observable behavior.

## What this guide builds

At the middle level, learn to **diagnose and repair the pattern in a component**. The goal is not perfect code; it is to make the next decision clearer and safer.

## Recognize the pattern

A harmless refactor breaks a test even though the user-visible behavior is unchanged.

Common signals:

- The intent is hard to infer from the call site or module boundary.
- A small change creates surprising work, delay, or risk elsewhere.
- The code needs an undocumented rule to stay correct.

## A better direction

Assert outcomes, use stable interfaces, and remove dependence on private details.

## Python example

```python
def test_total_includes_tax():
    order = Order(items=[Item(price=100)])
    assert order.total_with_tax() == 110
```

## Action checklist

- Trace callers and dependencies, choose an explicit trade-off, and explain the local design.
- Write down the behavior or constraint that must not change.
- Prefer a small, reversible step over a broad rewrite.
- Verify the result with the fastest relevant test, check, or measurement.

## Evidence of progress

A component-level change with evidence that behavior still holds.

## Check yourself

- What observable signal tells you this anti-pattern is present?
- What is the smallest change that reduces the risk?
- How will you know the improvement preserved the required behavior?
