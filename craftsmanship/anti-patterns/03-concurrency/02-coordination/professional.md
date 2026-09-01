# Coordination Anti-Patterns — Professional

> **Focus:** workers that wait, signal, retry, or cancel without a clear protocol.

## What this guide builds

At the professional level, learn to **make prevention a repeatable team practice**. The goal is not perfect code; it is to make the next decision clearer and safer.

## Recognize the pattern

Tasks can wait forever, duplicate work, or miss completion signals.

Common signals:

- The intent is hard to infer from the call site or module boundary.
- A small change creates surprising work, delay, or risk elsewhere.
- The code needs an undocumented rule to stay correct.

## A better direction

Define ownership, completion, timeout, cancellation, and retry rules before adding workers.

## Python example

```python
from queue import Queue

jobs = Queue()
jobs.put("send-email")
job = jobs.get()
try:
    handle(job)
finally:
    jobs.task_done()
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
