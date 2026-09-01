# Strangler Fig & Seams — Middle

> **Focus:** a legacy system is replaced in one risky move instead of gradually at a controlled boundary.

## What this guide builds

At the middle level, learn to **diagnose and repair the pattern in a component**. The goal is not perfect code; it is to make the next decision clearer and safer.

## Recognize the pattern

New and old behavior cannot be compared or rolled back safely.

Common signals:

- The intent is hard to infer from the call site or module boundary.
- A small change creates surprising work, delay, or risk elsewhere.
- The code needs an undocumented rule to stay correct.

## A better direction

Create a seam, route one capability through it, and move traffic incrementally.

## Python example

```python
def get_customer(customer_id, legacy, replacement, use_replacement):
    source = replacement if use_replacement else legacy
    return source.get(customer_id)
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
