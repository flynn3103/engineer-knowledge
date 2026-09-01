# Mixing Async and Blocking - Middle

> Put each kind of work on an execution resource suited to it.

```python
async def poll_job(job_id):
    # Suitable for a legacy blocking network SDK.
    return await asyncio.to_thread(warehouse_sdk.get_status, job_id)
```

`to_thread` suspends the coroutine while a pool thread blocks. It protects the
event loop, but does not make the call cheaper or automatically limit how many
calls are queued.

| Work | Mechanism | Why |
|---|---|---|
| Async Kafka/object-store client | await directly | Runtime owns readiness |
| Legacy blocking network client | bounded thread pool | Waiting releases loop |
| Python CPU transform | process pool/Spark | Threads remain GIL-limited |
| Native code releasing GIL | measured thread pool | Can use cores, but verify |

```python
limit = asyncio.Semaphore(16)

async def bounded_poll(job_id):
    async with limit:
        return await asyncio.to_thread(warehouse_sdk.get_status, job_id)
```

The semaphore bounds admitted work rather than allowing an executor's hidden
queue to absorb overload. Preserve deadlines: a timeout around the await may
stop waiting while the underlying thread and remote call continue.

## Test yourself

1. Why is a thread pool suitable for blocking I/O but often not Python CPU work?
2. What does the semaphore protect that `to_thread` alone does not?
3. Does cancelling the await forcibly terminate the pool thread?

Continue to [`senior.md`](senior.md).
