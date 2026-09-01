# Async Programming Anti-patterns - Professional

> Async architecture must be reviewed as lifecycle plus queueing plus scheduler
> behavior; local code style cannot prove system safety.

## Systemic hazards in real runtimes

**Node.js** makes blocking obvious at the language level but native add-ons,
synchronous APIs, giant JSON operations, and microtask chains can still starve
the event loop. Promise fire-and-forget without rejection handling produces
unowned failure; unlimited `Promise.all` creates eager fan-out.

**.NET** exposes the classic sync-over-async trap: blocking on `Task.Result`
while a continuation targets the captured context can deadlock. In ASP.NET Core,
the more common failure is ThreadPool starvation from blocking requests. `async
void` outside event handlers has no awaitable completion or normal exception
channel.

**Rust/Tokio** prevents many memory races but not scheduler misuse. A future that
does CPU work without yielding starves its worker. Dropping a future cancels it
by destruction, so cancellation-unsafe operations must preserve invariants
across any `await`. Detached `JoinHandle`s lose structured ownership.

**Kotlin**'s `GlobalScope` and careless `SupervisorJob` usage disconnect failure
and lifetime from component ownership. Catching broad `Exception` may consume
`CancellationException`, turning cancelled coroutines into shutdown leaks.

## Capacity mathematics

Async reduces per-wait overhead; it does not remove capacity limits. For arrival
rate `lambda`, service time `W`, and in-system work `L`, Little's Law still gives
`L = lambda W`. When a dependency slows from 50 ms to 5 s at 2,000 requests/s,
occupancy grows from roughly 100 to 10,000 before retries. If each task retains
100 KiB of payload and context, that is about 1 GB.

Fan-out multiplies this number. A request spawning 50 children at 1,000 requests/s
creates 50,000 child operations/s. Put budgets at the semantic operation level,
not only at the executor or socket level.

## Review and operations

Dashboard admitted, queued, active, completed, failed, cancelled, rejected, and
abandoned work. Include oldest task age, loop lag, blocking-pool queue time,
downstream in-flight count, and retry amplification ratio.

An incident runbook should first stop amplification: disable or budget retries,
reduce admissions, and protect critical traffic. Capture task/thread dumps and
profiles, determine whether timed-out work is still executing, then restore
capacity. Restarting without eliminating amplification often recreates the
outage immediately.

## Design and ops checklist

- Prove async is solving dominant waiting rather than disguising CPU work.
- Assign owner, bound, deadline, failure channel, and shutdown policy per spawn.
- Bound task creation as well as active remote operations.
- Ban blocking event-loop calls and sync-over-async in automated checks/review.
- Propagate cancellation to the actual dependency; measure abandoned work.
- Apply one retry budget across layers with exponential backoff and jitter.
- Audit cancellation safety at every await inside invariant-sensitive code.
- Exercise dependency stalls, cancellation storms, and rolling shutdowns.
- Keep escape hatches (`GlobalScope`, detached tasks, `async void`) rare and named.

```text
ASYNC REVIEW CHEAT SHEET
purpose       overlap waiting, not CPU computation
ownership     every task belongs to a scope/component
capacity      bound creation, execution, queues, and downstream work
cancellation  caller timeout != underlying work stopped
scheduler     no blocking or long non-yielding callbacks
failure       every exception has an observer
```

## Test yourself

1. A timeout dashboard looks healthy while memory grows. How would you test for
   abandoned underlying work?
2. Review an API that launches 50 child requests per call. Where must capacity
   limits and deadline budgets live?
3. Why can a supervisor construct improve availability but silently lose errors?
4. Which runtime-specific static checks would you add to CI?

## Further reading

- Bob Nystrom, "What Color is Your Function?"
- Nathaniel J. Smith, "Go Statement Considered Harmful."
- Stephen Toub, .NET async and ThreadPool starvation articles.
- Tokio tutorial, spawning, blocking, and cancellation safety documentation.
- Kotlin coroutine exception handling and supervision documentation.
- libuv design documentation and Node.js event-loop guidance.
