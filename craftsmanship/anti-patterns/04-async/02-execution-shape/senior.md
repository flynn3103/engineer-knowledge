# Async Execution-Shape Anti-Patterns — Senior

> **Focus:** accidental serial work, unbounded fan-out, and blocking work inside async paths.

## What this guide builds

At the senior level, learn to **contain risk across a changing system boundary**. The goal is not perfect code; it is to make the next decision clearer and safer.

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

- Map impact, stage the change, define rollback or containment, and validate the important assumptions.
- Write down the behavior or constraint that must not change.
- Prefer a small, reversible step over a broad rewrite.
- Verify the result with the fastest relevant test, check, or measurement.

## Evidence of progress

A migration or improvement plan with measurable guardrails.

## Check yourself

- What observable signal tells you this anti-pattern is present?
- What is the smallest change that reduces the risk?
- How will you know the improvement preserved the required behavior?
