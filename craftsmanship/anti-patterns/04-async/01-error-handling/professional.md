# Async Error-Handling Anti-Patterns — Professional

> **Focus:** lost exceptions, unobserved failures, and error paths with no owner.

## What this guide builds

At the professional level, learn to **make prevention a repeatable team practice**. The goal is not perfect code; it is to make the next decision clearer and safer.

## Recognize the pattern

Work fails in the background and callers continue as if it succeeded.

Common signals:

- The intent is hard to infer from the call site or module boundary.
- A small change creates surprising work, delay, or risk elsewhere.
- The code needs an undocumented rule to stay correct.

## A better direction

Await or supervise every task, add context to errors, and decide how failure reaches the caller.

## Python example

```python
import asyncio

async def load_profile(client, user_id):
    try:
        return await client.get(user_id)
    except TimeoutError as exc:
        raise RuntimeError(f"profile timed out: {user_id}") from exc
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
