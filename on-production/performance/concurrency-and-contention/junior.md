# Concurrency and Contention — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Concurrency and Contention** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Performance](../README.md) → Concurrency and Contention
> *You have eight CPU cores and a slow program. The obvious fix — "split the work across all eight" — is right about half the time. The other half, you add seven more threads and the program gets slower. This page is about telling the two cases apart.*

---

## Core Concept 1 — Concurrency Is Not Parallelism

These two words get used interchangeably, and that confusion is the source of most "why isn't it faster" surprises. They are different things.

- **Concurrency** is about *structure*: breaking a program into independent tasks that *could* run in overlapping time. A single-core machine can be concurrent — it just rapidly switches between tasks, giving the *illusion* of simultaneity.
- **Parallelism** is about *execution*: literally running tasks at the same instant, which requires multiple cores.
- Rob Pike's canonical line: *concurrency is dealing with many things at once; parallelism is doing many things at once.* Concurrency **organises** work; parallelism **executes** it faster.

Why this matters for speed:

- Concurrency is *necessary* for parallel speedup — you can't run things in parallel if you never split the work — but it is **not sufficient**.
- You can write perfectly concurrent code that runs no faster:

```go
// Concurrent in structure — but does this run in PARALLEL?
var wg sync.WaitGroup
for i := 0; i < 8; i++ {
    wg.Add(1)
    go func() {
        defer wg.Done()
        doWork()
    }()
}
wg.Wait()
```

- Whether these 8 goroutines actually run on 8 cores at once depends on:
  - How many cores the runtime is allowed to use (`GOMAXPROCS`, which defaults to the number of CPUs).
  - Whether the work is independent enough to *stay* on separate cores instead of piling up on a shared resource.
- If `doWork()` spends its whole time grabbing the same lock, you have 8 concurrent goroutines and *zero* parallel speedup — they take turns.

> **Key insight:** Concurrency is a design choice you make in your code; parallelism is a runtime outcome you can only *hope* for. Splitting work into goroutines is the price of admission, not the prize. The prize — actual speedup — only arrives if the split work can run *without waiting on each other*.

---

## Core Concept 2 — Contention: The One Checkout Lane

- Picture a supermarket with ten shoppers and **one open checkout lane**.
  - It does not matter that ten shoppers are ready to go — they finish at the rate of one lane.
  - Adding more shoppers does not add throughput; it just makes the queue longer.
  - The cashier (the shared resource) is the bottleneck, and everyone else waits.
- This is **contention**, and a lock is exactly that one checkout lane. When many threads need the same lock, only one holds it; the rest **block** — they stop doing useful work and wait in line.

Watch it happen — a counter that 8 goroutines hammer, protected by a single mutex:

```go
type Counter struct {
    mu sync.Mutex
    n  int64
}

func (c *Counter) Inc() {
    c.mu.Lock()         // ← the checkout lane. Only one goroutine past here at a time.
    c.n++               // critical section — trivially fast
    c.mu.Unlock()
}
```

- Run `Inc()` millions of times across 8 goroutines. You added 8× the workers — but every single one must pass through `c.mu.Lock()`, one at a time.
- The increment itself takes nanoseconds; the *waiting in line* to get the lock dominates.
- On a contended counter like this, the 8-goroutine version is frequently **slower** than the 1-goroutine version — you also pay the cost of goroutines fighting over the lock (cache-line ping-pong, scheduler wakeups) on top of zero parallelism in the critical section.

A rough, illustrative scaling curve for "all threads hit one lock constantly":

| Goroutines | Naive expectation | Reality (heavy contention) |
|---|---|---|
| 1 | 1.0× (baseline) | 1.0× |
| 2 | 2.0× | ~0.9× |
| 4 | 4.0× | ~0.7× |
| 8 | 8.0× | ~0.6× |

The numbers go the *wrong direction* because the lock is a single lane and the extra threads add only coordination overhead.

> **Key insight:** Throughput is capped by your most-contended shared resource, not by how many threads you start. One lock that everybody needs makes your program effectively single-threaded *inside that lock* — plus the overhead of the fight. Find the one lane everyone's queuing for; that's your real bottleneck.

---

## Core Concept 3 — Amdahl's Law: The Serial Part Caps You

- Almost no real program is 100% parallelisable. There's always a chunk that *must* run one-at-a-time: reading the input, the contended lock, writing the final result, the part you didn't bother to split.
- **Amdahl's Law** is the simple, brutal arithmetic of what that serial chunk does to your speedup.
- The intuition, no formula needed: *the time the serial part takes is a floor you can never get below, no matter how many cores you throw at the parallel part.*

Worked example — a job is 80 seconds of work, 20% serial (16s that can't be split), 80% perfectly parallelisable (64s):

- The 64 parallel seconds, on infinite cores, approach **0**.
- The 16 serial seconds stay **16** — forever.
- Best possible total: **16 seconds** — a maximum speedup of **5×**, even on a thousand cores.

Just 20% serial work caps you at 5×. Here's the curve:

| Cores | Speedup with 20% serial |
|---|---|
| 1 | 1.0× |
| 2 | 1.7× |
| 4 | 2.5× |
| 8 | 3.3× |
| 16 | 4.0× |
| ∞ | **5.0× (the ceiling)** |

- Notice the brutal **diminishing returns**: going from 1→2 cores buys you 0.7×; going from 8→16 cores buys another 0.7× but costs *eight more cores*.
- The serial fraction quietly eats every additional core.

> **Key insight:** Your speedup ceiling is set by the *serial fraction*, not the core count. Before you add cores, ask "what percent of this work genuinely cannot run in parallel?" If it's 20%, you'll never beat 5× — so adding the 9th, 17th, 33rd core is mostly wasted money. The highest-leverage performance work is often *shrinking the serial part*, not adding parallel capacity.

---

## Core Concept 4 — When Concurrency Actually Helps

Concurrency is a tool: it fits some jobs and ruins others. The decisive question is always: **what is the work actually waiting on?**

- **It helps — CPU-bound work that splits into independent pieces.**
  - Resizing 10,000 images, hashing a million records, summing a huge array in chunks.
  - Each piece needs a core and nothing else; give it 8 cores and you get close to 8× (minus the serial fraction from Concept 3). This is the textbook win.

  ```go
  // Independent CPU work — scales well across cores
  results := make([]int, len(items))
  var wg sync.WaitGroup
  for i := range items {
      wg.Add(1)
      go func(i int) {
          defer wg.Done()
          results[i] = expensiveCompute(items[i]) // writes its OWN slot — no shared lock
      }(i)
  }
  wg.Wait()
  ```

  - Each goroutine writes its own `results[i]` slot, so there's no contention — this is the good case.

- **It helps — overlapping I/O waits.**
  - Fetching 50 URLs, each taking 200ms of *network waiting*. Serially: 10 seconds.
  - Concurrently: each request mostly *waits*, and waiting is free — the CPU is idle anyway — so 50 requests overlap their waits and finish in ~200ms.
  - This isn't using more cores; it's using the *idle time during waiting*. Huge win, even on a single core.

- **It does NOT help — already saturated on one resource.**
  - If your 50 requests all hit *one* database that can only handle so many queries per second, concurrency doesn't speed them up — they queue at the database (Concept 2's checkout lane, again).
  - You're not I/O-*latency* bound, you're I/O-*throughput* bound on a single backend. Adding client threads just lengthens the queue.

- **It does NOT help — tiny tasks dominated by coordination.**
  - Spawning a goroutine, scheduling it, and synchronising the result costs a few hundred nanoseconds to a microsecond.
  - If each task is *also* only a few hundred nanoseconds of work, you spend more time coordinating than computing.
  - Summing a 100-element array across 8 goroutines is *slower* than a plain loop, every time.

> **Key insight:** Concurrency converts **independent work** and **idle waiting** into speed. It cannot speed up work that's serialised on a shared resource, and it actively *hurts* when the per-task work is smaller than the cost of handing it off. Match the tool to the bottleneck: parallelise CPU work that's truly independent; overlap I/O that's truly waiting; do *neither* when one resource is already the limit.

---

## Core Concept 5 — The Cost of a Lock, and Why You Hold It Briefly

A lock has two distinct costs, and conflating them hides the real problem.

1. **The uncontended cost** — taking a lock nobody else wants. Cheap: a single atomic CPU instruction, tens of nanoseconds. If your lock is rarely contended, this cost is negligible and you should not worry about it.
2. **The contended cost** — the *waiting* when someone else holds the lock. This is the expensive one, and it scales with **how long the holder keeps the lock**, multiplied by **how many threads are waiting**. This is where programs die.

The single most effective lock-performance rule follows directly: **hold the lock for as short a time as possible.** Everyone waiting is stuck for exactly as long as the current holder dawdles inside the critical section. Do slow things *outside* the lock.

The classic mistake — doing expensive work *while holding* the lock:

```go
// BAD: the slow call happens INSIDE the critical section.
// Every other goroutine waits for the network round-trip.
func (c *Cache) GetSlow(key string) string {
    c.mu.Lock()
    defer c.mu.Unlock()
    val := fetchFromNetwork(key)  // 50ms!  Lock held for 50ms.
    c.data[key] = val
    return val
}
```

- While one goroutine sits in `fetchFromNetwork` for 50ms, *every* other goroutine that wants this lock is frozen.
- Eight goroutines, and you've serialised 50ms apiece — 400ms of pure waiting.

The fix: do the slow work **outside** the lock, and only hold it for the fast map write:

```go
// BETTER: the 50ms network call is OUTSIDE the lock.
// The lock is held only for the nanosecond-scale map write.
func (c *Cache) GetFast(key string) string {
    val := fetchFromNetwork(key)  // 50ms, but NO lock held
    c.mu.Lock()
    c.data[key] = val             // microseconds, lock held briefly
    c.mu.Unlock()
    return val
}
```

- Now the lock is held for microseconds, not milliseconds — contention collapses.
- (A correctness-minded version would also avoid duplicate fetches, but that's the *right-answer* topic; the *fast* lesson is simply: shrink the critical section.)

> **Key insight:** The cost of a lock is dominated by the *duration of the critical section* under contention, not by the act of locking itself. A lock held for nanoseconds is nearly free even with many waiters; a lock held across a network call or disk read is a global stop sign. Optimise locks by making them *brief*, not by making them *fewer* — and never put I/O inside one.

---

## Real-World Examples

1. **The worker pool that got slower at 16 workers.**
   - A team parallelises a data-import job with a configurable worker count. At 4 workers it's 3× faster — great. At 16 workers it's *slower than 4*.
   - Profiling shows every worker, after processing a record, takes a single mutex to update a shared progress counter and a shared `map[string]int` of stats.
   - The actual processing parallelises fine; the shared counter is the one checkout lane, and 16 workers spend their time queueing for it.
   - Fix: each worker keeps a *local* counter and merges once at the end — contention vanishes, and 16 workers finally beat 4.

2. **The API that flew with concurrency.**
   - A service that aggregates data from 6 downstream APIs serially takes 6 × 150ms = 900ms per request.
   - Switching to 6 concurrent goroutines (each waiting on its own independent endpoint) drops it to ~160ms — the waits overlap.
   - This is the I/O-overlap win: no extra cores needed, because the goroutines spend their time *waiting*, and waits are free to overlap.
   - Note the contrast with example 1 — here the resources are *independent*, so concurrency works.

3. **The "parallel" sum that was pure overhead.**
   - A junior dev parallelises summing a 200-element slice across 8 goroutines to "use all the cores." It runs ~20× *slower* than a plain `for` loop.
   - Each goroutine does ~25 additions (nanoseconds) but costs hundreds of nanoseconds to spawn and synchronise. The coordination overhead dwarfs the work.
   - Lesson: parallelism has a fixed setup cost; the work per task must be *large enough* to pay it back.

---

## Common Mistakes

1. **Assuming threads add linearly to speed.** 8 threads almost never means 8× faster. The serial fraction (Amdahl) and the most-contended shared resource set a ceiling far below the core count. Measure the real speedup curve; don't assume it.

2. **One global lock everyone needs.** A single mutex guarding a shared counter, cache, or map turns your "parallel" code serial *inside that lock*, plus overhead. It's the one checkout lane. Shard the data, use per-worker locals, or atomics — give each shopper their own lane.

3. **Holding a lock during I/O.** A network call or disk read inside a critical section freezes every waiter for the full duration. Do slow work *outside* the lock; hold it only for the fast in-memory update.

4. **Parallelising tiny tasks.** If a task is smaller than the cost of spawning and synchronising it, concurrency loses every time. Batch tiny tasks into larger chunks so each goroutine does enough work to justify its setup cost.

5. **Throwing threads at an I/O-throughput bottleneck.** If 50 requests all hit one database maxed at 100 QPS, adding client goroutines just lengthens the queue at the database. You're saturated on *one resource* — more threads don't create more database capacity.

6. **Confusing "it's correct" with "it's fast."** `go test -race` passing means no data races — it says *nothing* about speed. A correct concurrent program can still be slower than the serial one. Correctness and performance are separate questions; verify both.

---

## Apply it

1. Choose one small, known input for **Concurrency and Contention**.
2. Predict the output or observable behavior.
3. Run the smallest example or probe that exercises the concept.
4. Change one input to trigger a failure or boundary case.
5. Explain the evidence using the guide's vocabulary.

## Verify your work

- Record the exact input, command or code path, and output.
- Repeat the probe and confirm the result is consistent.
- Show one expected success and one expected failure.
- Resolve any difference between the prediction and the evidence.

## Review questions

- What problem does Concurrency and Contention solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
- What is the difference between concurrency and parallelism, and why does the distinction matter for performance?
- Give an example of one workload where more cores help, one where overlapping I/O helps, and one where neither helps.
- A team made a single-threaded API handler `async` and saw no latency improvement under load. Why might that be?
- What does Amdahl's Law say about the ceiling on speedup from adding cores?
