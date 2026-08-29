# Reference Counting — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Reference Counting** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Refcounting vs Tracing GC: The Real Trade-off

The deepest insight (formalized by Bacon, Cheng, and Rajan in "A Unified Theory of Garbage Collection") is that **reference counting and tracing are duals.** Tracing computes liveness by starting from *live* roots and following references forward to find what survives; reference counting computes deadness by tracking when an object's incoming references reach *zero*. Real high-performance collectors are hybrids sitting somewhere between these poles. With that framing, the trade-offs are not religious but quantitative.

| Dimension | Reference Counting | Tracing GC |
|---|---|---|
| **When work happens** | Incrementally, on every reference op | In batches, at collection time |
| **Latency** | No global pauses; smooth | Stop-the-world or concurrent pauses |
| **Throughput** | Often *worse* — pays on every assignment | Often *better* — touches only live objects, amortized |
| **Promptness** | Immediate; finalizers run at last use | Eventual; object lingers until next collection |
| **Cycles** | Cannot reclaim alone | Reclaimed naturally |
| **Memory overhead** | Count per object; near-zero slack | Needs headroom (often 1.5–3×) to be efficient |
| **Cache behavior** | Writes to count = scattered dirtying | Touches live set during trace |
| **Cross-thread cost** | Atomic ops, contention | Synchronization at collection points |

The headline counterintuitive result: **naive reference counting usually has *worse* throughput than a good generational tracing collector**, even though intuition says "freeing immediately must be efficient." The reason is that refcounting does a tiny bit of work on *every* pointer write, including the vast majority of objects that die young and could have been bulk-reclaimed almost for free. Tracing touches only the survivors. This is why JVMs, Go, and high-performance runtimes chose tracing GC, not refcounting, for throughput.

Conversely, refcounting wins decisively on **pause-free determinism, prompt resource release, and predictable memory footprint** — which is why systems languages (C++, Rust) and resource-centric platforms (Swift/Cocoa, with its many OS handles) chose it.

## Advanced Optimizations

Naive refcounting's per-pointer-write cost is the thing to attack. The major techniques:

### Deferred reference counting (DRC)

The observation: the overwhelming majority of reference updates are to **local variables on the stack/in registers** — short-lived, churned constantly. Counting these is pure overhead. DRC **omits count updates for stack references** and instead, periodically, scans the stack to reconcile. Objects whose heap count is zero but which might still be referenced from the stack are placed in a "zero count table" and only freed after a stack scan confirms no stack reference remains. This removes the bulk of count traffic at the price of giving up *some* promptness (an object may briefly outlive its last use until reconciliation).

### Coalesced reference counting

Between two points where the heap is observed, a pointer field may be reassigned many times: A→B→C→D. The *net* effect on counts is only "release the original A, retain the final D"; the intermediate B and C churn cancels out. Coalescing logs the *old* value of a field on its first mutation in an epoch and computes net count deltas in bulk, collapsing many updates into few. This dramatically cuts atomic traffic for hot, frequently-mutated fields.

### Biased reference counting

Designed for the atomic-cost problem and used in **Swift** (and proposed for Python). Most objects are predominantly accessed by **one owning thread**. Biased RC splits the count into two: a **biased (owner-local, non-atomic)** count and a **shared (atomic)** count. The owning thread mutates its non-atomic count cheaply; only *other* threads pay the atomic cost. The two are merged at deallocation. This recovers much of `Rc`-like speed even for shared objects, as long as access is mostly single-owner — which empirically it usually is.

### One-bit / sticky counts and immortal objects

Many objects are referenced exactly once, or are effectively permanent (interned strings, `None`, small integers, type objects). Implementations use **one-bit reference counts** for the common single-reference case (overflow to a side table), and **immortal/sticky** counts that, once "stuck," are never decremented — so truly permanent objects pay zero count traffic. CPython's "immortal objects" (PEP 683) freeze the counts of singletons like `None`, `True`, and small ints precisely so free-threaded Python doesn't contend on their refcounts.

## Cross-Language Implementation Survey

### CPython

- **Inline `ob_refcnt`** in every `PyObject`. Non-atomic, historically GIL-protected.
- **Generational cyclic GC** (3 generations) layered on top, based on Bacon–Rajan trial deletion over container objects.
- **Immortal objects** (PEP 683) and **biased/deferred refcounting** (PEP 703) are the enabling tricks for **free-threaded Python (no-GIL)** — because the GIL's removal exposes every refcount update to contention. Free-threaded Python is *hard* in large part because of refcount contention on shared objects.

### Swift / Objective-C (ARC)

- **Compiler-inserted retain/release.** ARC analyzes object lifetimes at compile time and emits `swift_retain`/`swift_release` calls; there is no runtime GC.
- **Atomic counts** (Swift uses **biased refcounting** to reduce that cost), inline header bits with **side-table** spillover for weak references and overflow.
- **`weak`** (zeroing, becomes `nil` safely) and **`unowned`** (non-zeroing, faster, but unsafe if the object dies first) for cycle breaking.
- Retain cycles in **closures** are the classic Swift bug — a closure captures `self` strongly while `self` retains the closure; fixed with `[weak self]` / `[unowned self]` capture lists.

### Rust

- **`Rc<T>`**: non-atomic, single-thread, cheap. **`Arc<T>`**: atomic, thread-safe, costlier. The split is enforced by the type system (`Rc` is `!Send`).
- **`Weak<T>`** with `strong_count`/`weak_count`; `upgrade()` returns `Option`.
- Counts are inline in the heap allocation alongside the value.
- **No cycle collector** — Rust accepts that cycles *can* leak (`Rc` cycles are safe but leak) and pushes the programmer toward `Weak` or ownership redesign. Leaking is memory-safe in Rust, just wasteful.
- **Interior mutability** (`RefCell`/`Cell` for `Rc`, `Mutex`/`RwLock` for `Arc`) is needed to *mutate* through a shared pointer, since shared `Rc`/`Arc` give shared (immutable) access.

### C++

- **`shared_ptr<T>`** with a **control block** holding the strong count, the weak count, and the deleter. The control block is separately allocated unless you use `make_shared`, which fuses object + control block into one allocation (better locality, one alloc).
- **Atomic** strong/weak counts (always — the standard mandates thread-safe count manipulation, though the *pointee* is not protected).
- **`weak_ptr`** for non-owning references; `.lock()` to upgrade.
- **`enable_shared_from_this`** lets an object hand out `shared_ptr`s to itself without creating a second, independent control block (which would double-free).
- No cycle collection; cycles leak. `weak_ptr` is the prescribed fix.

## Code Examples

### Rust: the `Rc`/`Arc` decision and interior mutability

```rust
use std::rc::Rc;
use std::sync::Arc;
use std::cell::RefCell;
use std::sync::Mutex;

// Single-threaded shared, mutable: Rc + RefCell (non-atomic count, non-atomic borrow check)
let shared = Rc::new(RefCell::new(vec![1, 2, 3]));
shared.borrow_mut().push(4);

// Multi-threaded shared, mutable: Arc + Mutex (atomic count, locked data)
let shared_mt = Arc::new(Mutex::new(0u64));
let s2 = Arc::clone(&shared_mt);           // atomic increment
std::thread::spawn(move || { *s2.lock().unwrap() += 1; });
```

The cost asymmetry is explicit in the types: you pay atomic only by writing `Arc`.

### Swift: the closure retain cycle and its fix

```swift
class Downloader {
    var onDone: (() -> Void)?
    func start() {
        // BUG: closure captures self strongly; self holds onDone -> cycle
        onDone = { self.cleanup() }
        // FIX:
        onDone = { [weak self] in self?.cleanup() }
    }
    func cleanup() {}
}
```

### C++: `enable_shared_from_this` to avoid a second control block

```cpp
struct Widget : std::enable_shared_from_this<Widget> {
    std::shared_ptr<Widget> self() {
        return shared_from_this();   // shares the EXISTING control block
        // returning shared_ptr<Widget>(this) would create a SECOND
        // control block -> double free.
    }
};
```

## When Refcounting Wins, When It Loses

**Refcounting wins when:**

- **Pauses are unacceptable** (real-time audio, UI, soft-real-time control). No stop-the-world.
- **Prompt resource release matters** — RAII over OS handles, locks, GPU/DB resources. The destructor runs *now*, at last use.
- **Memory is tight** — refcounting runs close to the live set without the 1.5–3× headroom tracing prefers.
- **Single-threaded or single-owner** access dominates — non-atomic / biased counting is cheap.
- **Predictable footprint** is required (embedded, memory-constrained devices).

**Refcounting loses when:**

- **Raw throughput is king** — server batch processing, compilers, anything where total CPU on GC matters more than pause distribution. Generational tracing wins.
- **Cycles are pervasive and hard to make weak** — arbitrary graph data, doubly-linked structures, observer webs. The cycle collector eats the determinism advantage.
- **Heavy cross-thread sharing of hot objects** — atomic count contention serializes cores. This is the no-GIL Python pain point.
- **Allocation rate is very high with young death** — refcounting pays per-pointer-write even for objects that die immediately; a generational nursery reclaims those almost free.

## Coding Patterns

- **Ownership graph design first.** Decide the *direction* of ownership; make every back-edge weak. Cycles are prevented at design time, not collected at runtime.
- **`make_shared`/`Rc::new` once, clone cheaply** — but be aware each clone is a count op; in hot loops pass `&Rc`/`&Arc` (a borrow) instead of cloning.
- **Confine then share.** Build and mutate objects single-threaded (cheap `Rc`), and only `Arc`-wrap at the point you cross a thread boundary.
- **Immortalize true singletons.** For permanent, widely-shared objects, prefer mechanisms that stop counting them (statics, leaked `'static` refs, immortal objects) to eliminate contention.

## Best Practices

- **Profile count traffic, not just allocations.** A throughput regression from refcounting often shows up as time spent in `retain`/`release`/`Arc::clone`, not in the allocator.
- **Match the flavor to the access pattern.** Single-owner → non-atomic/biased; multi-reader hot object → consider not refcounting it at all (immortal, arena, or borrow).
- **Treat cycles as design smells.** A needed cycle collector in a refcounted system is a signal your ownership model has bidirectional edges; ask whether weak refs or restructuring removes them.
- **Don't fuse control block and object blindly.** `make_shared` improves locality but ties the object's memory lifetime to the *weak* count too — a lingering `weak_ptr` keeps the whole fused block allocated.

## Edge Cases & Pitfalls

- **`make_shared` + long-lived `weak_ptr` = retained storage.** The object's destructor runs at strong-zero, but the *memory* isn't freed until weak-zero because object and control block share one allocation. A `weak_ptr` that outlives everything pins the block.
- **`unowned`/`shared_from_this(this)` foot-guns.** `unowned` access after the object dies is undefined behavior; constructing a second control block from a raw `this` double-frees.
- **Deferred counting weakens promptness.** If you rely on DRC, you lose the "freed exactly at last use" guarantee — destructors may run late.
- **Biased count migration cost.** When an object escapes its owner thread, biased refcounting must transition it to the shared path — a one-time cost that can surprise under sharing-heavy workloads.
- **Cycle collector and finalizers interact badly.** Objects with finalizers inside a cycle complicate collection ordering; CPython historically refused to collect cycles containing objects with `__del__` (relaxed in modern versions, but still subtle).

---

## Apply it

1. State the system invariant that **Reference Counting** must protect.
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

- Which invariant must remain true when Reference Counting fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
