# Why Async — Middle

<!-- level-focus -->
At middle level, focus on this question:

> How can a single thread actually service thousands of connections
> simultaneously via an event loop?

Prerequisite: [`junior.md`](junior.md).

---

## One thread, many connections, via OS-level readiness notification

```mermaid
flowchart LR
    Connections["10,000 connections\n(mostly idle, waiting)"] --> OS["OS-level readiness API\n(epoll/kqueue/io_uring)"]
    OS --> EventLoop["ONE event loop thread\nasks: 'which of these\n10,000 are ACTUALLY ready\nwith data RIGHT NOW?'"]
    EventLoop --> Handle["Only handles the FEW\nthat are actually ready -\ndoesn't need a dedicated\nthread per connection at all"]
```

Instead of a dedicated OS thread blocking on each individual connection,
async I/O uses an OS-level readiness API (`epoll` on Linux, `kqueue` on
BSD/macOS, `io_uring` more recently, IOCP on Windows) that lets **one**
thread ask the OS: "of these 10,000 file descriptors I care about, which
ones actually have data ready right now?" — and only processes those,
handling potentially thousands of connections' worth of readiness checks
in one syscall, on one thread.

## The memory math

```mermaid
flowchart LR
    ThreadModel2["10,000 threads:\n~10,000 x few MB\nstack = tens of GB"] --> Compare["vs."]
    Compare --> AsyncModel2["10,000 async tasks:\neach just a small\nstate machine/coroutine\nobject - kilobytes\ntotal, not gigabytes"]
```

An async "connection" is typically just a small data structure (a state
machine tracking where it is in its request-handling logic) rather than
an entire OS thread with its own stack — this is the direct mechanism
behind async's dramatically lower per-connection memory cost, which is
`professional.md`'s subject in precise numbers.

> 🎓 **Takeaway:** the event loop's core trick is replacing "one thread
> blocked per connection" with "one thread asking the OS which of many
> connections need attention right now" — turning thousands of blocking
> waits into one efficient, batched readiness check.

## Test yourself

1. Why does asking the OS "which of these are ready" in one call scale
   better than having a dedicated thread block on each connection
   individually?
2. Why is an async task's memory footprint typically much smaller than a
   full OS thread's?
3. What does `epoll`/`kqueue` actually return, conceptually, when you ask
   it "which connections are ready"?

Continue to [`senior.md`](senior.md).
