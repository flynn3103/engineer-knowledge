# N+1 in Code — Junior

> **Focus:** a loop triggers one expensive lookup or operation for each item.

## What this guide builds

At the junior level, learn to **recognize the pattern in a small change**. The goal is not perfect code; it is to make the next decision clearer and safer.

## Recognize the pattern

Latency or load grows roughly with the number of records.

Common signals:

- The intent is hard to infer from the call site or module boundary.
- A small change creates surprising work, delay, or risk elsewhere.
- The code needs an undocumented rule to stay correct.

## A better direction

Batch the lookup, prefetch needed data, or change the interface to accept many keys.

## Python example

```python
def load_orders(repository, user_ids):
    orders_by_user = repository.find_for_users(user_ids)
    return [orders_by_user.get(user_id, []) for user_id in user_ids]
```

## Action checklist

- Name the smell, find the smallest affected boundary, and make one safe improvement.
- Write down the behavior or constraint that must not change.
- Prefer a small, reversible step over a broad rewrite.
- Verify the result with the fastest relevant test, check, or measurement.

## Evidence of progress

A short before/after note and a focused test or check.

## Check yourself

- What observable signal tells you this anti-pattern is present?
- What is the smallest change that reduces the risk?
- How will you know the improvement preserved the required behavior?
