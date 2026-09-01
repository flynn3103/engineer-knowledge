# Async Execution-Shape Anti-Patterns — Professional

> **Focus:** accidental serial work, unbounded fan-out, and blocking work inside async paths.

## What this guide builds

At the professional level, learn to **make prevention a repeatable team practice**. The goal is not perfect code; it is to make the next decision clearer and safer.

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
