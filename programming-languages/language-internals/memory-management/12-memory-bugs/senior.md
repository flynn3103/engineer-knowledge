# Memory Bugs — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Memory Bugs** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The unified taxonomy of "RSS is too high"

When a senior sees memory climbing, they branch on **four** systemic causes, not one:

1. **Reachable-object leak (retention).** Your references keep growing the live set. The cure is breaking references / bounding collections. Diagnosed by dominator analysis.
2. **Fragmentation.** The live set is flat, but the allocator/GC can't pack it densely, so RSS stays high. Cure depends on the allocator: compaction, size-class tuning, or restructuring allocations.
3. **Off-heap / native growth.** The managed heap is flat and clean; memory grows outside it. Cure: track native allocations explicitly; this is invisible to heap dumps.
4. **Allocation churn / GC pressure.** Live set flat, but allocation *rate* forces the GC to thrash — a latency/CPU bug presenting as a memory symptom. Cure: reduce allocation.

The senior skill is *cheaply distinguishing these four* before committing to an expensive investigation. The RSS-vs-live divergence, GC logs (frequency, pause times, post-GC occupancy), and native-memory accounting are the three readings that disambiguate them.

### 2. Fragmentation: why free memory you can't use

Fragmentation is the bug juniors don't know exists and seniors design around.

**External fragmentation** happens in non-compacting allocators and collectors. You free objects, leaving holes; later a large request can't fit in any single hole even though total free space is ample. A long-running C/C++ service with mixed allocation sizes, or a JVM using a non-compacting collector under certain conditions, can have a "live set" of 2 GB but an RSS of 5 GB — *the 3 GB gap is fragmentation, not a leak.* No heap dump will ever explain it, because every byte is legitimately structured; it's just badly packed.

**Compacting collectors** (e.g., a moving generational GC) dodge external fragmentation by relocating survivors into contiguous space, which also enables cheap bump-pointer allocation. The trade-off: compaction costs CPU and requires updating every reference to a moved object. This is the central design tension — *non-moving collectors are simpler and avoid relocation cost but fragment; moving collectors avoid fragmentation but pay to relocate.*

**Internal fragmentation** is the quieter tax. Allocators serve from size classes, so every allocation rounds up. A workload dominated by 33-byte objects landing in 48-byte slots wastes ~30% — silently, forever, with no leak anywhere. This is why allocation *shape* (the distribution of sizes) matters as much as allocation *volume*.

### 3. Off-heap leaks: the heap dump's blind spot

The most painful production leaks are the ones your primary tool can't see. Direct `ByteBuffer`s in Java are a heap-tiny wrapper around a large native buffer; the wrapper is freed only when *it* is GC'd, and native memory isn't reclaimed until then — so a low-pressure heap can sit on gigabytes of native buffers indefinitely. JNI global references, `mmap`'d files, native image/crypto/compression libraries, and cgo allocations in Go are all in this category.

The senior reflex: **when the managed heap is provably clean but RSS climbs, stop heap-dumping and start native-accounting.** On the JVM that means Native Memory Tracking (`-XX:NativeMemoryTracking`), `pmap`, and `jcmd VM.native_memory`. In native code it means `valgrind`/`massif` or ASan's LeakSanitizer. The failure mode here is *category error*: spending a day in a heap analyzer that, by construction, cannot show the leak.

### 4. Retention as an architectural property

At scale, you don't fix leaks one reference at a time; you design lifetimes so leaks can't accumulate. The systemic patterns:

- **Bounded by construction.** Every cache is an LRU/TTL/size-capped structure, never a raw map. Every queue has a max depth and a drop/back-pressure policy. The leak-resistant property is *structural*, enforced by the type, not by reviewer vigilance.
- **Ownership is explicit.** One owner is responsible for a resource's lifetime; everyone else borrows. RAII (C++), `defer close` (Go), try-with-resources (Java), and `Drop` (Rust) all encode "this *will* be released" into control flow. Leaks happen where ownership is *ambiguous* — shared mutable references with no clear releaser.
- **Weak references for back-edges.** Caches keyed on objects, observer registrations, and parent/child back-pointers use weak references so the collector can reclaim despite the reference. (Java `WeakHashMap`, soft references for memory-sensitive caches.)
- **Lifetime-scoped allocation.** Arenas/pools tie a batch of objects to a request or task; the whole batch is released at once. Powerful for churn, but a single escaping pointer turns it into a use-after-free (non-GC) or a leak (if the arena outlives expectation).

### 5. Churn as a GC-pressure systemic bug

A system can be leak-free and fragmentation-free and *still* be a memory disaster because it allocates too fast. Every short-lived object is work for the collector. Defensive copying, autoboxing (`Integer` per `int`), per-request allocation in hot paths, and excessive intermediate collections in stream pipelines can push allocation rate to gigabytes/second, forcing constant minor GCs and tail-latency spikes. The senior treats *allocation rate* as a first-class SLI and uses pooling, value types, slice reuse, and `sync.Pool`-style mechanisms to flatten it — while staying alert that pooling reintroduces lifetime bugs (a pooled object used after return is the manual-memory bug class sneaking back in).

---

## Code Examples

### Java: a classloader leak (the app-server classic)

```java
// In a redeployable web app, a library starts a thread referencing app classes:
public class CacheManager {
    static { startBackgroundThread(); } // never stopped on undeploy
}
```

On redeploy, the container discards the old `WebAppClassLoader`, but the still-running background thread holds a reference to a class loaded by it. That class's classloader retains *every* class and static of the old app. Result: each redeploy leaks a full copy of the application's class metadata, eventually exhausting Metaspace. The dominator-tree fingerprint is a `Thread` (a GC root) dominating an entire `WebAppClassLoader`. The fix is lifecycle: stop the thread in a `ServletContextListener.contextDestroyed`.

### Java: weak-reference cache to make retention collectible

```java
// Entries vanish automatically once the key is unreachable elsewhere.
private final Map<Key, Value> cache = new WeakHashMap<>();
// For memory-sensitive caches that may keep values until pressure:
private final Map<Key, SoftReference<Value>> soft = new ConcurrentHashMap<>();
```

`WeakHashMap` lets the GC reclaim entries whose keys are otherwise dead — the cache stops being a leak by construction. (Caveat: weak/soft caches have surprising eviction timing; for predictable bounds prefer an explicit LRU.)

### Go: bounding churn with sync.Pool (and the lifetime hazard)

```go
var bufPool = sync.Pool{New: func() any { return make([]byte, 0, 4096) }}

func handle(r io.Reader) {
    buf := bufPool.Get().([]byte)[:0]
    defer bufPool.Put(buf[:0])
    // ... use buf; MUST NOT retain it past Put, or it's a data race / corruption
}
```

This flattens allocation rate under load. The systemic risk: pooling reintroduces manual lifetime management — a pooled buffer used after `Put` is the use-after-free bug class returning through the back door.

### Detecting off-heap growth on the JVM

```bash
# Start with: -XX:NativeMemoryTracking=summary
jcmd <pid> VM.native_memory summary   # categorizes native usage (Thread, Code, GC, Internal...)
pmap -x <pid> | sort -k3 -n | tail    # largest native mappings; spot direct buffers / mmap
```

When `VM.native_memory` shows "Internal" or "Other" ballooning while the heap is flat, you've confirmed an off-heap leak no `.hprof` would ever reveal.

---

## Coding Patterns

- **Bounded-by-type:** caches are LRU/TTL types, queues have capacity, batches have limits — bounds enforced by the data structure, not the reviewer.
- **Single-owner + borrow:** one lifecycle owner per resource; everyone else holds a non-owning view; release is in the owner's `defer`/`finally`/`Drop`.
- **Weak back-edges:** observer lists, caches keyed on live objects, and parent pointers use weak references so they never anchor.
- **Scope-bound allocation:** request-scoped arenas/pools with a hard guarantee that nothing escapes the scope.
- **Native-accounting hooks:** every off-heap allocation path is wired to a metric so native growth is observable, not invisible.

---

## Best Practices

1. **Branch on the four causes early.** Don't open a heap dump until the RSS-vs-live + GC-log reading says the leak is actually *in the heap.*
2. **Make bounds structural.** Replace every raw map/list cache with a size/TTL-bounded type. Reviewer vigilance does not scale; types do.
3. **Treat allocation rate as an SLI.** Track bytes-allocated/sec and GC CPU%; a flat heap can still be a churn incident.
4. **Account for native memory explicitly.** Enable NMT/equivalent; export native usage to dashboards. The heap view is a blind spot by design.
5. **Encode lifetime in control flow.** RAII / `defer close` / try-with-resources / `Drop` make actual lifetime track intended lifetime automatically.
6. **Audit redeploys and pools as leak surfaces.** Classloader leaks and pooled-object misuse are senior-grade traps that pass casual review.
7. **Prefer compaction when fragmentation is the risk; prefer arenas when churn is the risk** — and know you can't have both for free.

---

## Edge Cases & Pitfalls

- **"It's a leak" when it's fragmentation.** Days lost heap-dumping a flat live set. If the dump is clean and RSS is high, suspect fragmentation or off-heap before re-reading the dump.
- **Pooling that becomes corruption.** A `sync.Pool` / object-pool buffer retained past return reintroduces use-after-free/aliasing. Pools trade GC pressure for manual lifetime risk — sometimes a bad trade.
- **Soft/weak caches with nondeterministic eviction** cause latency cliffs (mass eviction under pressure, then cold-start storms). Bounds you can't predict are bounds you can't capacity-plan.
- **Compaction isn't free and isn't always available.** Some collectors don't compact certain spaces (e.g., metaspace, large-object areas), so those regions still fragment.
- **Native leaks survive heap reset.** Forcing a full GC won't reclaim `mmap`/JNI memory whose wrappers are still reachable; you must release the native handle.
- **Arena escape is silent.** A pointer that outlives its arena is fine in tests and catastrophic under the right interleaving — invisible until production load.
- **Internal fragmentation has no smoking gun.** No single object is at fault; the *distribution* of sizes is. It only shows up as a persistent gap between live bytes and committed bytes.

---

## Apply it

1. State the system invariant that **Memory Bugs** must protect.
2. Mark ownership, state, and failure propagation at each boundary.
3. Compare two designs under load, dependency failure, and future change.
4. Define recovery and compatibility behavior before implementation.
5. Test the riskiest assumption with a focused experiment.

## Verify your work

- The experiment supports the design with evidence, not preference.
- Failure injection shows the blast radius and recovery path.
- Compatibility checks cover old and new callers or data.
- Operational signals reveal invariant violations and recovery progress.

## Review questions

- Which invariant must remain true when Memory Bugs fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
