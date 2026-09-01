# Synchronization Misuse Anti-Patterns — Junior

> **Focus:** unsafe locking, lock ordering, and synchronization that does not protect the real invariant.

## What this guide builds

At the junior level, learn to **recognize the pattern in a small change**. The goal is not perfect code; it is to make the next decision clearer and safer.

## Recognize the pattern

Shared values can be observed or changed in an invalid state.

Common signals:

- The intent is hard to infer from the call site or module boundary.
- A small change creates surprising work, delay, or risk elsewhere.
- The code needs an undocumented rule to stay correct.

## A better direction

Protect one invariant with one clear synchronization strategy and keep critical sections small.

## Python example

```python
from threading import Lock

class Counter:
    def __init__(self):
        self._value, self._lock = 0, Lock()

    def increment(self):
        with self._lock:
            self._value += 1
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
