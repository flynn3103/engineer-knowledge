# Async Runtimes - Professional

> Runtime choice is a choice of scheduler, I/O backend, wake-up protocol,
> blocking strategy, and observability surface.

## Named runtime internals

**Tokio** uses per-worker local queues, a global injection queue, and work
stealing. Futures are polled cooperatively through `Waker`; Mio supplies the
readiness layer over epoll, kqueue, or IOCP. A future that performs long work
without returning `Poll::Pending` monopolizes a worker. `spawn_blocking` uses a
separate, generously sized pool, so callers still need semantic bounds to avoid
turning overload into thousands of queued blocking jobs.

**libuv**, used by Node.js, runs an event loop with platform backends and a
thread pool for filesystem, DNS, and selected native work. The default
`UV_THREADPOOL_SIZE` is small; one slow class of operation can head-of-line block
unrelated pool users. JavaScript callbacks remain serialized on the loop thread,
so one CPU-heavy callback inflates latency for every connection.

**CPython asyncio** schedules callbacks and tasks on an event loop, normally one
thread. SelectorEventLoop uses readiness APIs; Windows defaults to a proactor
loop backed by IOCP. `run_in_executor` and `to_thread` preserve loop progress but
do not remove the GIL limit for CPU-bound Python bytecode.

**.NET** composes `Task`, `SynchronizationContext`, IOCP completion, and a
hill-climbing ThreadPool. Blocking on `Task.Result` or `.Wait()` can deadlock
context-bound applications and causes thread-pool starvation in services.
Starvation triggers thread injection, but ramp-up delay produces severe tail
latency before capacity catches up.

## Failure at 10x and 100x load

At 10x concurrency, memory per task, socket limits, timer management, and remote
service quotas usually fail before raw scheduler throughput. At 100x, wake-up
storms, allocator pressure, queue contention, and telemetry cardinality become
first-order costs. A one-kilobyte task footprint becomes roughly 1 GB at one
million tasks before payload buffers and tracing context.

Fairness is not guaranteed by cooperative schedulers. Measure maximum poll or
callback duration, not just average loop utilization. A runtime can report 60%
CPU while p99 timers are seconds late because several workers are monopolized.

## Operability

Dashboard ready-queue depth, task count by state, loop or timer lag, poll/callback
duration, blocking-pool active threads and queue delay, steals, wake-ups, and
shutdown duration. Correlate these with file descriptors, CPU throttling, GC,
and downstream latency.

Runbook for rising loop lag:

1. Capture runtime task dumps and CPU profiles before restarting.
2. Find callbacks or polls exceeding the scheduling budget.
3. Check blocking-pool saturation and accidental synchronous calls.
4. Compare runnable work with CPU quota and worker count.
5. Bound admission; then offload, partition, or shorten monopolizing work.

## Design and ops checklist

- Match readiness/completion support to required operating systems and APIs.
- Assign one owner for runtime creation and graceful shutdown.
- Bound tasks, sockets, blocking queues, and downstream concurrency separately.
- Isolate blocking work classes when starvation domains differ.
- Define a maximum cooperative scheduling interval and instrument violations.
- Load-test cancellation storms, timer storms, and downstream stalls.
- Preserve trace context without unbounded per-task cardinality.
- Prefer measured queueing and tail latency over synthetic task-spawn rates.

```text
RUNTIME CHEAT SHEET
reactor       turns I/O readiness/completion into wake-ups
scheduler     chooses which ready task runs next
cooperative   task must yield; runtime cannot preempt arbitrary code
blocking pool isolates unavoidable synchronous waits
bounds        tasks != sockets != threads != downstream capacity
```

## Test yourself

1. A service has low CPU but five-second timer lag. Which runtime metrics and
   task evidence would separate blocking callbacks from downstream waiting?
2. Why is Tokio's large blocking pool not an overload-control mechanism?
3. How does .NET ThreadPool starvation differ operationally from a blocked
   Node.js event loop?
4. What fails first when a design moves from 10,000 to one million tasks?

## Further reading

- Tokio source: `tokio/src/runtime/scheduler`; Tokio runtime metrics docs.
- libuv design overview and `src/unix/core.c` event-loop implementation.
- CPython source: `Lib/asyncio/base_events.py` and `selector_events.py`.
- Stephen Toub, .NET ThreadPool and async performance writings.
- Matt Welsh et al., "SEDA: An Architecture for Well-Conditioned, Scalable
  Internet Services."
