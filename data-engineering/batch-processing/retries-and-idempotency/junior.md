# Retries & Idempotency — Junior

<!-- level-focus -->
At junior level, focus on this question:

> Why can retrying a failed job immediately, with no delay, make things
> worse instead of better?

---

## The naive retry

```python
def call_with_retry(fn, max_attempts=5):
    for attempt in range(max_attempts):
        try:
            return fn()
        except Exception:
            continue  # immediately try again
    raise Exception("All attempts failed")
```

If the failure was caused by the downstream service being **overloaded**
(too many requests, not enough capacity), retrying immediately adds
**more** load to an already-struggling system, at the exact moment it can
least handle it.

```mermaid
flowchart LR
    Overload["Downstream service\nis overloaded, starts failing"] --> Retry["Every failed caller\nimmediately retries"]
    Retry --> More["MORE load hits the\nalready-struggling service"]
    More --> Worse["Service degrades further,\nmore requests fail,\nmore immediate retries..."]
    Worse -.-.-> Retry
```

This is a **retry storm** — a positive feedback loop where retries
themselves become the dominant source of load, actively preventing the
struggling service from recovering, potentially turning a brief blip into
an extended outage.

## The fix starts with: don't retry instantly

Introducing **any** delay between attempts gives the downstream service a
chance to recover before the next wave of requests arrives — the simplest
version is a fixed delay (`wait 1 second, then retry`), though `middle.md`
covers why a smarter delay strategy is needed for this to work well at
scale.

> 🎓 **Takeaway:** a retry is a bet that the failure was transient. If many
> callers retry at the same instant with no delay, that bet can become a
> self-fulfilling prophecy that the failure *stays* transient forever,
> because the retries themselves are now the problem.

## Test yourself

1. Why does immediate retry specifically make an *overload*-caused failure
   worse, while it might be harmless for a failure caused by, say, a single
   corrupted record?
2. What's the simplest possible fix to reduce (not eliminate) retry-storm
   risk, before considering anything more sophisticated?
3. If 10,000 clients all experience a failure at the exact same moment and
   all retry after exactly the same fixed 1-second delay, what problem
   still exists?

Continue to [`middle.md`](middle.md).
