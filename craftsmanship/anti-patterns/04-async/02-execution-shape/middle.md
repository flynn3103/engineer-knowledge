# Async Execution-Shape Anti-Patterns — Middle

> **Focus:** accidental serial work, unbounded fan-out, and blocking work inside async paths.

## What this guide builds

At the middle level, learn to **diagnose and repair the pattern in a component**. The goal is not perfect code; it is to make the next decision clearer and safer.

## Recognize the pattern

The code looks concurrent but has the wrong throughput, ordering, or resource use.

Common signals:

- The intent is hard to infer from the call site or module boundary.
- A small change creates surprising work, delay, or risk elsewhere.
- The code needs an undocumented rule to stay correct.

## A better direction

Choose the desired shape: sequential, bounded parallel, streaming, or background work.

## Python example

```python
import asyncio

async def fetch_all(client, ids):
    tasks = [client.get(item_id) for item_id in ids]
    return await asyncio.gather(*tasks)
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
