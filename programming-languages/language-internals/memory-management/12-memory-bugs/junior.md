# Memory Bugs — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Memory Bugs** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The leak you can have even with a garbage collector

Here is the whole problem in one sentence: **if you put objects into a long-lived collection and never take them out, that collection is a leak.**

```java
// A "cache" that is really a memory leak.
private static final Map<String, User> CACHE = new HashMap<>();

User getUser(String id) {
    return CACHE.computeIfAbsent(id, this::loadFromDb);
}
```

This looks harmless. But `CACHE` is `static`, so it lives for the entire lifetime of the program. Every distinct `id` ever requested adds an entry. Nothing is ever removed. The GC can never collect those `User` objects — they're reachable through `CACHE`, which is reachable through a static field, which is a root. After enough unique requests, the heap fills and you OOM.

The fix isn't "add more RAM." The fix is to **bound** the cache: cap its size, evict old entries, or expire them after a while. We'll return to that.

### 2. Live set versus allocated memory

When you watch memory climb, you need to distinguish two numbers:

- **Live set:** how much your program *genuinely* needs (reachable objects).
- **Allocated / RSS:** how much memory is *currently held* by the process.

A healthy program: live set stays roughly flat over time (it goes up and down with load but returns to a baseline). RSS may sit a bit above the live set — that's normal, the runtime keeps some slack.

A leaking program: the live set climbs steadily and never comes back down. Every GC cycle reclaims less than the program allocated, so the floor rises. That **rising floor** is the signature of a leak.

### 3. The symptoms you'll actually observe

You rarely *see* the leak directly at first. You see one of these:

- **Slow OOM:** runs fine for hours, then crashes. Classic unbounded-growth leak.
- **Memory climbs and plateaus high:** it stops growing but never drops back, even when traffic dies down at night. Could be a leak that hit a natural ceiling, fragmentation, or a cache that filled.
- **Latency spikes / "stuttering":** GC is running constantly trying to keep up with allocation. This is *GC pressure*, often from creating too many short-lived objects (churn), not necessarily a leak.
- **Container gets killed but the app logs nothing:** the OS OOM-killer struck. The app didn't get a chance to throw — RAM simply ran out (often native/off-heap memory the GC doesn't manage).

Learning to map a symptom to a likely cause is half the skill. A junior who can say "memory rises and never falls under steady load — that smells like an unbounded collection" is already ahead.

### 4. Why "it's the GC's fault" is almost always wrong

New engineers blame the garbage collector. In nearly every real case, the GC is doing exactly its job: keeping alive everything that's reachable. The bug is in *your* references. Reframe every memory investigation as a single question:

> **"What is keeping this object alive?"**

Find the reference chain back to a root, and you've found the leak.

---

## Code Examples

### Example 1 — The unbounded map leak (and the fix)

```go
// LEAK: sessions are added but never removed.
var sessions = map[string]*Session{}

func login(id string) {
    sessions[id] = newSession()
}
// Every login grows the map. Logouts that don't delete leak forever.
```

The fix is to make removal part of the lifecycle:

```go
func logout(id string) {
    delete(sessions, id) // now the Session becomes unreachable and collectible
}
```

If sessions should also expire on their own, you add a time-based sweep — but the core lesson is: **every `add` needs a corresponding `remove`, or a bound.**

### Example 2 — The lapsed listener (forgotten callback)

```java
class Button {
    private final List<Listener> listeners = new ArrayList<>();
    void addListener(Listener l) { listeners.add(l); }
    void removeListener(Listener l) { listeners.remove(l); } // must be called!
}
```

If a short-lived screen registers a listener with a long-lived `Button` and never calls `removeListener`, the `Button` holds the screen alive forever. The screen *should* be garbage after you navigate away, but it isn't — it's reachable through the button's listener list. Always pair `add` with `remove`, often in a teardown/dispose method.

### Example 3 — Watching the floor rise

You don't always need fancy tools to *spot* a leak. Logging your own heap usage on a timer is enough to confirm one:

```go
import "runtime"

func logHeap() {
    var m runtime.MemStats
    runtime.ReadMemStats(&m)
    // HeapAlloc = bytes of allocated, still-reachable heap objects (the live-ish set)
    log.Printf("HeapAlloc = %d MiB", m.HeapAlloc/1024/1024)
}
```

Run this every 30 seconds under steady load. If `HeapAlloc` keeps climbing and never settles, you have a leak. This simple loop is often the first thing you reach for before pulling out a profiler.

---

## Best Practices

1. **Bound every collection that grows from external input.** If a map, list, or cache can grow with traffic, give it a maximum size, a TTL, or both. An unbounded cache is a leak with extra steps.
2. **Pair every `add` with a `remove`.** Listeners, sessions, subscriptions, pending requests — if something goes in, design the path for it to come out.
3. **Be suspicious of `static` / global mutable collections.** They live forever, so anything they hold lives forever.
4. **Watch the floor, not the peak.** Judge memory health by the post-GC baseline over time, not by momentary spikes.
5. **Log heap usage on a timer in dev/staging.** A one-line periodic log of live heap turns "I think it's leaking" into "it's definitely leaking, here's the slope."
6. **Don't blame the GC.** Ask "what's keeping this alive?" instead. The answer is a reference chain you control.

---

## Edge Cases & Pitfalls

- **"It's not leaking, it's just slow to free."** Some runtimes return memory to the OS lazily, so RSS can stay high after the live set shrinks. Before declaring a leak, confirm the *live set* (post-GC heap) is actually rising — not just RSS.
- **A cache is not automatically a leak.** A *bounded* cache that hovers at its limit is healthy. The leak is the *unbounded* one. Don't panic at a flat-but-high plateau.
- **The dev box "never leaks."** Leaks need time and traffic. A bug that takes six hours of production load to OOM will look perfectly fine in a five-minute local run. Reproduce under sustained load.
- **Big allocations aren't always leaks.** A program that legitimately loads a 2 GB dataset uses 2 GB. Memory being *high* is only a bug if it's *unboundedly growing* or *far above what the workload needs.*
- **Restarting "fixes" it — and hides it.** Auto-restart on OOM masks slow leaks for months. The metric to watch is *memory slope between restarts*, not just crash frequency.
- **Native memory is invisible to the heap view.** If you're using off-heap buffers, image libraries, or native extensions, your language's heap tool may show nothing while RSS climbs. That's a more advanced case, but know it exists so you don't chase the wrong thing.

---

## Apply it

1. Choose one small, known input for **Memory Bugs**.
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

- What problem does Memory Bugs solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
