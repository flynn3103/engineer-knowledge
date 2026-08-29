# Memory Bugs — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Memory Bugs** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The leak mechanism catalog

Unbounded collections are the obvious case. The instructive ones are subtler:

**Closures capturing more than you think.** A closure keeps alive *everything it references*, even fields you never use:

```go
func handler(huge *BigBuffer) func() {
    return func() {
        log.Println("done") // never touches huge...
        _ = huge            // ...but the closure still captures it
    }
}
```

If that returned function is stored somewhere long-lived (a registry, a timer, a callback list), `huge` is pinned for as long as the closure lives. The Java analog is an anonymous inner class capturing `this`, dragging the whole enclosing object along.

**Go slice / substring retention.** Re-slicing keeps the *entire* backing array alive:

```go
func firstLine(data []byte) []byte {
    i := bytes.IndexByte(data, '\n')
    return data[:i] // returns a tiny slice that PINS the whole `data` array
}
```

If `data` is 100 MB and you keep the 20-byte result in a cache, you've retained 100 MB. The cure is to *copy* what you need: `append([]byte(nil), data[:i]...)`. The same trap existed in Java's `String.substring` before JDK 7u6, where a substring shared the parent string's `char[]`.

**Goroutine / thread leaks.** A goroutine blocked forever on a channel never returns, so its stack — and everything it references — never gets collected:

```go
func leak(ch chan int) {
    go func() {
        val := <-ch // if nobody ever sends, this goroutine lives forever
        process(val)
    }()
}
```

Every call spawns a goroutine that never dies. Goroutine count climbs in lockstep with memory. This is why `runtime.NumGoroutine()` is a leak indicator as valuable as heap size.

**ThreadLocal leaks in pooled threads.** Thread pools reuse threads, so a `ThreadLocal` you set and forget lives as long as the *pool*, not your request:

```java
private static final ThreadLocal<HeavyContext> CTX = new ThreadLocal<>();
// set per request, never removed -> the worker thread retains HeavyContext forever
```

The fix is a `try/finally` that calls `CTX.remove()`.

**Lapsed listeners / observers.** Covered at junior level, but worth restating as a *mechanism*: a long-lived publisher holds short-lived subscribers, inverting the lifetime you intended.

### 2. Retention versus churn — two different problems

These get conflated constantly, and they need opposite fixes.

- **Retention bug (a leak):** objects accumulate and are never released. The *live set grows over time.* Fix: break the reference / bound the collection. Diagnosed with **heap dumps + dominator trees.**
- **Churn / allocation pressure:** objects are created and discarded rapidly. The live set may be *flat*, but the *allocation rate* is enormous, so the GC runs constantly — CPU burns and latency spikes. Fix: allocate less (reuse, pool, avoid boxing). Diagnosed with **allocation profiles.**

A program can have flat memory and still be "sick" with churn. A program can have low CPU and still be leaking. Knowing which one you're chasing decides which tool you reach for.

### 3. Retained size is the number that matters

When you open a heap dump, *shallow size* (the object itself) is almost useless for finding leaks. The cache `HashMap` object is tiny; what matters is its **retained size** — the megabytes of `User` objects it keeps alive. The dominator tree exists precisely to compute and rank retained sizes, so you can find the *one* object whose removal frees the most.

### 4. RSS vs live-heap divergence is itself a diagnosis

| Live heap (post-GC) | RSS | Likely cause |
|---|---|---|
| Rising | Rising | Classic reachable-object leak |
| Flat | Rising | Fragmentation or **native/off-heap** leak |
| Flat | Flat-high after a spike | Runtime not returning memory to OS (often benign) |
| Flat | Flat | Healthy |

This 2×2 is one of the most useful triage tools you'll learn. If your Java heap dump looks clean but RSS climbs, *stop looking at the heap* — the leak is in direct `ByteBuffer`s, JNI, or memory the OS hasn't reclaimed. Chasing the wrong region wastes days.

---

## Code Examples

### Go: capturing a heap and an allocation profile with pprof

```go
import (
    "net/http"
    _ "net/http/pprof" // registers /debug/pprof handlers
)

func main() {
    go func() { http.ListenAndServe("localhost:6060", nil) }()
    // ... your service ...
}
```

Then, under load:

```bash
# Retention: what is alive right now (inuse_space is the default)
go tool pprof http://localhost:6060/debug/pprof/heap

# Churn: what has been allocated cumulatively (alloc_space)
go tool pprof -alloc_space http://localhost:6060/debug/pprof/heap

# Goroutine leak check
curl -s http://localhost:6060/debug/pprof/goroutine?debug=1 | head
```

Inside `pprof`, `top` ranks the biggest holders, and `list <func>` shows the exact lines. The `inuse_space` vs `alloc_space` distinction is the retention-vs-churn distinction made concrete.

### Go: the slice retention fix

```go
// Leaky: result pins the whole `raw` backing array.
func extract(raw []byte) []byte {
    return raw[10:20]
}

// Fixed: copy detaches the small slice from the large array.
func extractCopy(raw []byte) []byte {
    out := make([]byte, 10)
    copy(out, raw[10:20])
    return out
}
```

### Java: confirming a listener leak with a heap dump

```bash
# Capture a heap dump from a running JVM (use the live flag to force a GC first)
jmap -dump:live,format=b,file=heap.hprof <pid>
```

Open `heap.hprof` in Eclipse MAT, run the **Leak Suspects** report, and look at the dominator tree. A classic result: a single `EventBus` instance with a retained size of hundreds of MB, dominating a `List<Listener>` full of objects that should have been garbage. The path-to-GC-root view names the exact static field rooting it.

### Java: ThreadLocal cleanup

```java
try {
    CTX.set(buildContext());
    handle(request);
} finally {
    CTX.remove(); // critical on pooled threads, or the worker retains it forever
}
```

---

## Diagnosis Methodology

A repeatable sequence beats poking around:

1. **Confirm it's a leak, not noise.** Watch the post-GC floor over a sustained run. Rising floor under steady load → real leak. Distinguish from churn by checking GC frequency/CPU and allocation rate.
2. **Classify with the RSS-vs-live 2×2.** Heap rising → look in the heap. Heap flat, RSS rising → look off-heap/native. This decides which tool you even open.
3. **Reproduce under load.** Leaks need traffic and time. Build the smallest repeatable load that makes the slope visible — ideally faster than production so you iterate in minutes, not hours.
4. **Capture the right artifact.** Retention → heap dump (or two, for a diff). Churn → allocation profile. Goroutine/thread leak → goroutine/thread dump.
5. **Rank by retained size / dominators.** Don't read the dump top-to-bottom. Let the dominator tree (or `pprof top`) point at the biggest holder.
6. **Walk the retention path to a root.** Convert "this is big" into "this is *rooted* by X." That's the actual bug.
7. **Fix the reference, then re-measure.** Bound the collection, copy the slice, close the goroutine, `remove()` the thread-local. Re-run the same load and confirm the floor is now flat.

The discipline is: *measure, classify, capture, rank, trace, fix, re-measure.* Skipping classification (step 2) is the most common time-sink — people heap-dump a native-memory leak and find nothing.

---

## Coding Patterns

- **Copy-to-trim:** when returning a small slice/substring of a large buffer, copy it so the big backing store can be collected.
- **Bounded cache:** replace `HashMap` caches with an LRU/TTL cache that evicts.
- **Lifecycle pairing:** every `register`/`set`/`add`/`go` has a matching `unregister`/`remove`/`delete`/cancellation, ideally in `defer`/`finally`.
- **Context cancellation for goroutines:** pass a `context.Context` and `select` on `ctx.Done()` so blocked goroutines can exit.

---

## Best Practices

1. **Always reproduce under load before profiling.** A leak you can't trigger is a leak you can't verify you fixed.
2. **Diff two heap dumps** rather than staring at one — growth is more legible than absolute size.
3. **Match the tool to the symptom:** retention → heap/dominator; churn → allocation profile; off-heap → native tooling. Use the RSS-vs-live 2×2 to choose.
4. **Track goroutine/thread count as a first-class metric.** It catches a whole class of leaks the heap size alone hides.
5. **Read retained size, not shallow size.** The big *holder* is rarely big itself.
6. **Re-measure after every fix.** "Looks better" is not "the floor is flat under the same load."

---

## Edge Cases & Pitfalls

- **Heap dump on a constrained container can OOM-kill the process** while dumping. Dump to a mounted volume, raise the limit temporarily, or capture from a replica.
- **`alloc_space` looks alarming but isn't retention.** Huge cumulative allocation with a flat live set is *churn*, not a leak. Read the right profile.
- **Sampling profilers miss the small-but-frequent.** A 16-byte object allocated a billion times can dominate churn yet barely appear; tune the sampling rate when results look incomplete.
- **The slice/substring trap is invisible in the small.** It only bites when the backing array is large and the retained slice is long-lived. Reviews rarely catch it; load tests do.
- **`ThreadLocal.remove()` forgotten on async/reactive code** is even worse than on thread pools — work hops threads and contexts leak across requests.
- **A clean heap dump does not exonerate you.** If RSS is the thing climbing, the heap dump *should* look clean. Believing "the dump is fine, so there's no leak" sends you in circles. Trust the 2×2.

---

## Apply it

1. Find a real component where **Memory Bugs** affects an interface or dependency.
2. Write two plausible choices and the constraint that favors each one.
3. Make the smallest reversible change at that boundary.
4. Exercise the component alone, then exercise the integrated flow.
5. Keep the decision note with the evidence that selected the option.

## Verify your work

- A focused check proves the local behavior.
- An integrated check proves callers and dependencies still agree.
- Logs, traces, compiler output, or benchmarks expose the boundary.
- Reverting the change restores the previous behavior without unrelated edits.

## Review questions

- Which boundary is most affected by Memory Bugs?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
