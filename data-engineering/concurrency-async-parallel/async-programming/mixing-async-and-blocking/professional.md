# Mixing Async and Blocking - Professional

> A sync/async boundary is a queueing system with cancellation, ownership, and
> shutdown semantics, not merely an executor call.

## Runtime-specific traps

In **Node.js/libuv**, synchronous filesystem and crypto APIs block the sole
JavaScript loop. Async filesystem, DNS, and selected crypto operations share
libuv's worker pool; saturating it can delay unrelated operations. Increasing
`UV_THREADPOOL_SIZE` raises concurrency but also memory, contention, and pressure
on the downstream resource.

In **CPython asyncio**, `to_thread` uses the default executor and propagates
`contextvars`, but cancellation cannot safely kill arbitrary Python threads.
The awaiter can be cancelled while the function continues. Process pools avoid
the GIL for CPU work but add serialization, process startup, memory, and failure
recovery costs.

In **Tokio**, blocking inside an async task monopolizes a scheduler worker.
`spawn_blocking` moves work to a separate pool, but started blocking closures
generally cannot be cancelled. Tokio may create many blocking threads, so
compute-heavy use still needs a semaphore or Rayon-style compute pool.

In **.NET**, sync-over-async (`.Result`, `.Wait()`) can deadlock when a
continuation needs the captured `SynchronizationContext`. In servers it more
often creates ThreadPool starvation: requests occupy threads waiting for tasks
whose continuations need threads from the same depleted pool.

## Queueing and failure behavior

If arrivals exceed completions, any executor with an unbounded queue has
unbounded latency and memory. Little's Law, `L = lambda W`, makes the growth
visible: 2,000 arrivals/s at five seconds mean roughly 10,000 operations in the
system. A timeout that abandons but does not stop work can make measured client
latency look bounded while occupancy continues growing.

At 10x load, queue delay and downstream connection limits dominate. At 100x,
thread stacks, context switching, process-pool copies, and cancellation cleanup
can collapse the host. Shed work before enqueueing when the deadline cannot be
met.

## Operations

Dashboard executor submissions, active workers, queue depth and age, execution
time, abandoned operations, rejection count, and event-loop lag. Tag by work
class rather than high-cardinality request identity.

For starvation: capture thread and task dumps, separate threads executing work
from threads synchronously waiting, inspect the oldest queued item, and verify
whether cancellation reaches the external client. Restoring capacity without
fixing admission merely postpones recurrence.

## Design and ops checklist

- Inventory every synchronous dependency reachable from event-loop code.
- Prefer native async APIs when their semantics and maturity are adequate.
- Use dedicated bounded pools for distinct latency or criticality classes.
- Apply admission control before enqueueing and preserve deadline budgets.
- Treat cancellation of the awaiter and cancellation of work separately.
- Prohibit nested waits on the same pool and sync-over-async at API boundaries.
- Define drain, cancellation, and replay behavior for shutdown.
- Load-test downstream hangs, not only successful service time.

```text
BOUNDARY CHEAT SHEET
async I/O       await on runtime poller
blocking I/O    bounded, isolated thread pool
CPU work        compute/process pool; account for copies
timeout         may abandon without stopping underlying work
overload        reject before an unbounded executor queue
```

## Test yourself

1. Why can increasing a blocking pool improve throughput and worsen p99 latency?
2. Design cancellation for a C library call that cannot be interrupted safely.
3. How would you prove a .NET incident is ThreadPool starvation rather than a
   downstream latency increase?
4. Which metrics reveal abandoned work continuing after caller timeouts?

## Further reading

- libuv documentation, "Thread pool work scheduling."
- CPython `asyncio.to_thread` and `concurrent.futures` source.
- Tokio documentation, "CPU-bound tasks and blocking code."
- Stephen Toub, "Are deadlocks still possible with await?"
- Neil J. Gunther, *Guerrilla Capacity Planning* (queueing and scalability).
