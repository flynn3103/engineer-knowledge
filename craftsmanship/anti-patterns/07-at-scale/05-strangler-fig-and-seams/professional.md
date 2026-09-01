# Strangler Fig & Seams — Professional

> **Focus:** a legacy system is replaced in one risky move instead of gradually at a controlled boundary.

## What this guide builds

At the professional level, learn to **make prevention a repeatable team practice**. The goal is not perfect code; it is to make the next decision clearer and safer.

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

- Set a shared rule, automate a useful signal, review trends, and adjust the practice from results.
- Write down the behavior or constraint that must not change.
- Prefer a small, reversible step over a broad rewrite.
- Verify the result with the fastest relevant test, check, or measurement.

## Evidence of progress

An operating practice that reduces recurrence without blocking delivery.

## Check yourself

- What observable signal tells you this anti-pattern is present?
- What is the smallest change that reduces the risk?
- How will you know the improvement preserved the required behavior?
