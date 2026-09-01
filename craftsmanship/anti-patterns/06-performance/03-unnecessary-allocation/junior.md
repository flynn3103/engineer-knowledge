# Unnecessary Allocation — Junior

> **Focus:** temporary objects or copies created repeatedly on a hot path.

## What this guide builds

At the junior level, learn to **recognize the pattern in a small change**. The goal is not perfect code; it is to make the next decision clearer and safer.

## Recognize the pattern

Profiling shows time or memory spent creating values that are immediately discarded.

Common signals:

- The intent is hard to infer from the call site or module boundary.
- A small change creates surprising work, delay, or risk elsewhere.
- The code needs an undocumented rule to stay correct.

## A better direction

Reuse only when measurement supports it; otherwise simplify the data flow and avoid needless copies.

## Python example

```python
def normalized_names(names):
    return [name.strip().lower() for name in names]

# One clear pass avoids building several intermediate lists.
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
