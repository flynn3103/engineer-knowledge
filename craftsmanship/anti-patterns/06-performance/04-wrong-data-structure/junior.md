# Wrong Data Structure — Junior

> **Focus:** a collection does not match the operations performed most often.

## What this guide builds

At the junior level, learn to **recognize the pattern in a small change**. The goal is not perfect code; it is to make the next decision clearer and safer.

## Recognize the pattern

Simple operations become unexpectedly slow as data grows.

Common signals:

- The intent is hard to infer from the call site or module boundary.
- A small change creates surprising work, delay, or risk elsewhere.
- The code needs an undocumented rule to stay correct.

## A better direction

List the dominant operations and choose a structure that makes them direct.

## Python example

```python
allowed_ids = {"a1", "b2", "c3"}

def is_allowed(user_id):
    return user_id in allowed_ids
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
