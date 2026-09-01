# Memory and Allocation Optimization — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Memory and Allocation Optimization** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Performance](../README.md) → Memory and Allocation Optimization
> *The middle page taught you to read a heap profile and cut allocations. This page is about why allocation costs what it costs: the size-class machinery inside the allocator, the write barriers and pacing logic inside the garbage collector, and the moment a per-object `malloc` should become an arena. Profiler tooling — pprof, heaptrack, async-profiler — lives next door in [01-profiling](../profiling/README.md); here we use the numbers those tools give you to reshape how memory actually flows.*

---

## How a Modern Allocator Works — Size Classes and Thread Caches

A general-purpose allocator (tcmalloc, jemalloc, Go's runtime allocator, glibc's ptmalloc) faces three pressures at once: it must be **fast** (the fast path runs on every allocation), **scalable** (many threads allocating concurrently must not serialize on one lock), and **space-efficient** (low fragmentation). Every modern design resolves these with the same two ideas: **size classes** and **per-thread caches**.

- **Size classes.** Instead of satisfying an arbitrary request size exactly, the allocator rounds up to one of a fixed set of sizes — Go uses ~68 classes (8, 16, 24, 32, 48, 64, 80, 96, 112, 128, … up to 32 KB); tcmalloc and jemalloc use similar geometrically-spaced ladders.
  - A request for 50 bytes is served from the 64-byte class. This turns allocation into "find the right class, pop a fixed-size object off that class's free list" — O(1), no first-fit search, no coalescing on the fast path.
  - The cost is **internal fragmentation**: those 14 wasted bytes per 50-byte object. Class spacing is the explicit knob trading wasted space against the number of classes; jemalloc's default wastes at most ~20% within a size class.
- **Per-thread / per-CPU caches.** The fast path must not take a global lock. So each thread (Go: each P, via `mcache`) keeps a small private cache of free objects per size class:

```
Go's allocator tiers (small objects, <32 KB):
  mcache   per-P, lock-free   pop a free object of the right size class      ← fast path
  mcentral per-size-class     refill an mcache's class from a shared span    ← contended, locked
  mheap    global             carve spans (runs of 8 KB pages) from the OS   ← slow path, may mmap
```

- tcmalloc and jemalloc mirror this: tcmalloc has a per-thread cache → central free list → page heap; jemalloc has per-thread caches (`tcache`) in front of multiple **arenas** (independent heaps, by default one per few CPUs) precisely so threads assigned to different arenas never contend.
- Large objects (Go: ≥32 KB) skip the cache tiers and go straight to the page-level heap.

```bash
# See which allocator a process actually uses (glibc malloc? jemalloc? tcmalloc?)
LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libjemalloc.so.2 ./app   # swap in jemalloc, no recompile
MALLOC_CONF=stats_print:true ./app                            # jemalloc: dump arena/bin stats at exit
```

> **Key insight:** Allocation is cheap *because* of the cache tiers and expensive *when you fall through them*. A tight loop allocating same-size objects stays in the lock-free per-thread cache and costs a few instructions each. The same loop under thread-cache exhaustion, or allocating sizes that miss the cached classes, drops to the contended central path. Allocation-cost spikes are usually "I fell out of the fast path," not "allocation got slower."

---

## Fragmentation, Working Set, and Why RSS Lies

Two processes with identical *live* heaps can have wildly different memory footprints. The gap is fragmentation plus retention policy.

- **Internal fragmentation** is waste *inside* an allocated block — the 14 bytes lost rounding 50 up to the 64-byte class, or struct padding. It is bounded and predictable (size-class spacing caps it at ~10–25%).
- **External fragmentation** is free memory that exists but is *unusable* because it is scattered in pieces too small (or too oddly placed) to satisfy a request. A heap with 500 MB free in 8-byte holes cannot serve a 4 KB request without going to the OS for more. Size-class allocators largely defeat external fragmentation *within* a class (every object in a span is interchangeable) but suffer it *across* spans: a span dedicated to the 64-byte class with one live object pins all 8 KB even though 127 slots are free. This is **span-level retention**, the dominant fragmentation mode in tcmalloc/jemalloc/Go.

**RSS vs live heap.** Resident set size (RSS) is what the OS thinks you're using — pages that are mapped and resident. Your live heap is what your program is actually keeping alive. These diverge for three independent reasons:

1. **Fragmentation** — spans/pages held for a few live objects each.
2. **Retention policy** — after a GC frees objects, the runtime may not return the pages to the OS immediately (returning them costs syscalls and re-faulting on reuse). Go uses `madvise(MADV_FREE)` (lazy: the page stays in RSS until the kernel needs it) by default on Linux; `MADV_DONTNEED` (eager: drops it from RSS now) under `GODEBUG=madvdontneed=1`. This is why a Go service's RSS can stay high long after a load spike even though the heap shrank.
3. **Off-heap mappings** — `mmap`'d files, off-heap buffers, thread stacks, JIT code caches, metaspace — none of which appear in a *heap* profiler but all of which are in RSS.

```bash
# The diagnostic question is always: heap or non-heap?
cat /proc/$PID/smaps_rollup     # RSS broken down: anon vs file-backed, shared vs private
jcmd $PID GC.heap_info          # JVM: live heap, separate from RSS
GODEBUG=gctrace=1 ./app         # Go: HeapInuse/HeapReleased vs process RSS
```

> **Key insight:** "Memory is high" is not a diagnosis. *Live heap high* means a leak or genuine bloat — chase it with a heap profiler. *RSS high but live heap low* means fragmentation or unreturned pages — chase it with `smaps`, allocator stats, and retention settings. They have opposite fixes; conflating them sends you optimizing the wrong layer.

---

## GC Algorithms and the Three-Way Trade-off

Every tracing garbage collector is a point in a space bounded by three quantities that cannot all be maximized at once:

```
        throughput  (fraction of CPU doing your work, not collecting)
            /\
           /  \
          /    \
   pause /------\ footprint
   time          (how much extra heap you keep to amortize collection)
```

- **Throughput** ↑ by collecting *less often* (bigger heap, more headroom) and *in bulk* (stop-the-world). Pays in pause time and footprint.
- **Pause time** ↓ by doing GC work *concurrently* with the application and *incrementally*. Pays in throughput (write barriers, coordination overhead) and often footprint (you collect before the heap is full).
- **Footprint** ↓ by collecting *eagerly* at a low heap target. Pays in throughput (more frequent collections) — this is the **allocation-rate / pause / heap-size** triangle in another guise.

The core algorithm families:

| Family | Idea | Trade-off |
|---|---|---|
| **Mark-sweep** | Mark reachable from roots, sweep the rest into free lists | Simple; no compaction → fragmentation; sweep is O(heap) |
| **Mark-compact** | Mark, then slide live objects together | Defeats fragmentation; compaction is expensive, usually STW |
| **Copying / semispace** | Copy live objects to a fresh space, abandon the old | Fast allocation (bump pointer), self-compacting; needs 2× space |
| **Generational** | Collect the *young* generation often, *old* rarely | Exploits the weak generational hypothesis; needs a write barrier |

- **The generational hypothesis** — *most objects die young* — is the single most exploited fact in GC design. If 90%+ of objects become garbage almost immediately, collecting a small young generation frequently reclaims most garbage for a small fraction of the cost of scanning the whole heap.
  - The price: when an *old* object points to a *young* one, the young collection must know about it without scanning the old generation — so every pointer write is intercepted by a **write barrier** that records cross-generational references (in a card table or remembered set). This is why generational GCs make every reference store slightly more expensive: it's the toll for cheap young collections.
- **Concurrent vs stop-the-world.** A STW collector freezes all application threads while it works — simple and high-throughput, but the pause scales with heap size (a 50 GB STW heap can pause for seconds). A *concurrent* collector does marking (and, in the best designs, compaction) while the application runs.
  - The hard part is **mutation during marking**: if the app rewrites pointers while the collector is tracing, the collector can miss a live object. This is solved by write (and sometimes read) barriers that maintain a tricolor invariant — the same barrier machinery, now serving concurrency instead of (or as well as) generations.

> **Key insight:** There is no "best" GC, only a best point on the triangle *for your workload*. A batch job wants throughput (big heap, STW is fine). A latency-SLO service wants bounded pauses (concurrent, pay throughput). A high-density multi-tenant box wants footprint (eager, small target). Choosing or tuning a collector is choosing which corner to sacrifice.

---

## The Go GC — Pacer, Write Barriers, and GOMEMLIMIT

Go's collector is a **concurrent, non-generational, non-moving, tricolor mark-sweep**. Two of those words surprise people: *non-generational* (Go bets that escape analysis + cheap stack allocation already keep most short-lived objects off the heap, so the generational win is smaller than in Java) and *non-moving* (objects never relocate, which keeps interior pointers and cgo-shared memory valid but means Go relies on size-class spans rather than compaction to manage fragmentation).

- **Tricolor marking with a write barrier.** Objects are white (unvisited), grey (visited, children pending), black (done). The invariant: *no black object may point to a white object* without the collector knowing.
  - Because the app mutates pointers during concurrent marking, Go inserts a **hybrid write barrier** (Yuasa-style deletion + Dijkstra-style insertion, since Go 1.8) on pointer writes during a GC cycle. The barrier shades the relevant objects grey so nothing live is missed — and crucially it lets Go avoid a STW stack re-scan, keeping pauses sub-millisecond.
  - The barrier is *off* outside a GC cycle, so it costs nothing when not collecting.
- **The pacer.** The central tuning question is *when to start* a concurrent cycle so it finishes just before the heap would otherwise overflow the target — start too early and you collect too often (throughput loss); too late and the heap blows past the target before the cycle ends.
  - `GOGC` (default 100) sets the target: heap may grow to `live × (1 + GOGC/100)` before the next cycle's goal. `GOGC=100` means "collect when the heap doubles relative to the live set after the last GC." `GOGC=200` collects half as often (more throughput, more footprint); `GOGC=50` twice as often (less footprint, more CPU).

```bash
GODEBUG=gctrace=1 ./app
# gc 42 @8.1s 1%: 0.018+1.2+0.004 ms clock, ...  4->5->2 MB, 5 MB goal, 8 P
#   1%         = fraction of CPU spent in GC since start
#   0.018+1.2+0.004 = STW-start + concurrent-mark + STW-end (ms) — note the tiny STW parts
#   4->5->2 MB = heap at start -> peak -> live after; "5 MB goal" = the pacer's target
```

- **GOMEMLIMIT** (Go 1.19) is the most important addition in years. `GOGC` alone is a *ratio* — it can't bound absolute memory, so a workload that grows its live set grows RSS unboundedly and gets OOM-killed in a container.
  - `GOMEMLIMIT` sets a **soft total-memory limit**: as the heap approaches it, the pacer collects more aggressively (effectively raising the GC frequency beyond what GOGC asked) to stay under the cap, trading CPU for survival.

```bash
GOMEMLIMIT=900MiB ./app        # soft cap ~90% of a 1Gi container; GC ramps up near it
# Pair with: set GOMEMLIMIT to (container limit − headroom for off-heap/stacks/CGO),
# and keep GOGC at default so steady state stays efficient and the limit is only a backstop.
```

> **Key insight:** Go's GC has essentially one tuning surface — heap *headroom*. `GOGC` sets it as a ratio (throughput vs footprint), `GOMEMLIMIT` sets it as an absolute backstop (survival vs CPU). You do not tune pauses directly because they're already tiny by design; you tune *how much memory you spend to keep them tiny*, and `GOMEMLIMIT` is how you stop that spend from getting you OOM-killed.

---

## The JVM Collectors — G1, ZGC, Shenandoah, and Off-Heap

The JVM ships several collectors precisely because the triangle has no universal answer; you pick by SLO.

- **G1 (Garbage-First, default since JDK 9).** Region-based (the heap is split into ~2048 equal regions), generational, mostly-concurrent marking with **STW evacuation** (it copies live objects out of selected regions to compact them).
  - G1 targets a *pause-time goal* (`-XX:MaxGCPauseMillis=200`) and picks how many regions to collect per pause to meet it — hence "garbage-first": it collects the regions with the most garbage for the best reclaim-per-pause.
  - Pauses are bounded but real (typically tens to low-hundreds of ms) and *do* grow with live-set size because evacuation is STW.
- **ZGC and Shenandoah (low-latency, concurrent compaction).** Both push pause time toward *constant, sub-millisecond, independent of heap size* — ZGC advertises pauses under ~1 ms on heaps from a few GB to terabytes.
  - They achieve this by doing **concurrent compaction**: relocating objects while the application runs. The enabling trick is a **load (read) barrier** plus **colored pointers** (ZGC) or **Brooks forwarding pointers** (classic Shenandoah): when the app dereferences a reference to an object mid-relocation, the barrier transparently fixes up the pointer to the object's new location.
  - The cost is throughput — read barriers run on loads, which are far more frequent than stores — and footprint (they need headroom to relocate into). ZGC is generational since JDK 21, which recovers much of the throughput gap.

```
              pause time        throughput        heap size scaling
G1            tens–100s ms      high              pause grows with live set
Shenandoah    < ~10 ms          medium            pause ~flat
ZGC           < ~1 ms           medium (better w/ gen)  pause flat to TB heaps
```

```bash
java -XX:+UseG1GC        -XX:MaxGCPauseMillis=200 -Xmx8g -Xlog:gc*:file=gc.log MyApp
java -XX:+UseZGC         -XX:+ZGenerational       -Xmx32g -Xlog:gc* MyApp
java -XX:+UseShenandoahGC -Xmx16g -Xlog:gc* MyApp
```

- **Off-heap on the JVM.** When even a low-pause collector can't keep up — multi-hundred-GB caches, or data you don't want the GC to scan at all — the move is to take memory *out of the managed heap*.
  - `ByteBuffer.allocateDirect` and the newer `java.lang.foreign` (Foreign Function & Memory API, JDK 22) allocate native memory the GC never traces; the object stays alive only as a small on-heap handle.
  - This is how Cassandra, Kafka's page-cache reliance, Netty's pooled `ByteBuf`s, and off-heap caches (Ehcache/Chronicle) keep enormous datasets resident without imposing GC scan cost.
  - The trade: you now manage lifetime manually (or via the FFM `Arena` scope), reintroducing the exact use-after-free and leak risks the GC existed to prevent.

> **Key insight:** On the JVM the collector choice *is* the latency decision: G1 for "low-effort, good-enough pauses with high throughput," ZGC/Shenandoah for "pauses must stay flat as the heap grows." And when the answer is "this data should not be GC-managed at all," off-heap is the escape hatch — paying manual-memory risk to buy GC-invisible footprint.

---

## Custom Allocation — Arenas, Slabs, Free Lists, and Pools at Scale

General-purpose allocators are general because they don't know your lifetimes. When you *do* know them, a custom strategy can beat malloc by an order of magnitude — but each has a precise sweet spot, and outside it they're a liability.

- **Arena / region allocation.** Allocate from a large contiguous block by bumping a pointer; *free everything at once* by resetting the pointer.
  - Per-object allocation is a pointer add and bounds check (a few instructions, zero metadata, zero fragmentation); per-object free does not exist.
  - The catch: you cannot free individual objects. This is perfect for **phase-scoped** lifetimes — everything allocated during one request, one compiler pass, one frame — where the whole batch dies together.

```rust
// Rust: bumpalo arena — allocate many short-lived nodes, drop the whole arena at once
let arena = bumpalo::Bump::new();
let node = arena.alloc(Node { value: 42, next: None });   // pointer bump, no per-object free
// ... build a whole graph in the arena ...
drop(arena);                                              // frees everything in one shot
```

- Rust makes arenas especially attractive because it has *no GC* — lifetimes are explicit, so an arena's "free everything at scope end" maps cleanly onto ownership. C++ does the same with monotonic buffer resources (`std::pmr::monotonic_buffer_resource`).
- **Slab allocation.** Pre-carve a block into fixed-size slots for *one* type, with a free list of slots. Allocation/free is push/pop on the free list — O(1), no fragmentation (every slot is identical), and excellent cache locality (objects of the same type packed together). This is the Linux kernel's `kmem_cache` and the model behind most object pools. Sweet spot: **many objects of one type, allocated and freed individually at high frequency** (inodes, network buffers, connection structs).
- **Free lists** are the primitive underneath both — a singly-linked list of reclaimed blocks, threaded through the free blocks themselves (no extra storage). They turn allocation into a list pop.
- **Object pools at scale.** Reuse expensive-to-construct objects instead of reallocating. Go's `sync.Pool` is the canonical case — a per-P cache of reusable objects that the GC may drain between cycles:

```go
var bufPool = sync.Pool{New: func() any { return new(bytes.Buffer) }}

func handle(w io.Writer, r io.Reader) {
    buf := bufPool.Get().(*bytes.Buffer)
    buf.Reset()                 // MUST reset — pooled objects carry old state
    defer bufPool.Put(buf)
    // ... use buf without allocating ...
}
```

- Pools pay off only when (a) construction is genuinely expensive *or* (b) the allocation rate is high enough that you're pressuring the GC.
- Real failure modes: a pool of *variable-size* buffers can retain the largest buffer ever seen forever (memory bloat), and a pooled object handed out without a reset is a correctness bug that leaks data across requests.

> **Key insight:** Custom allocators trade generality for a lifetime assumption. Arenas assume *batch death* (free all at once); slabs/pools assume *uniform type, individual reuse*. The win is real — arenas turn N frees into 1, pools turn allocation into a list pop and drop GC pressure — but only when your lifetimes actually match the assumption. Reach for them when a profiler shows allocation/GC dominating *and* the lifetimes are regular; otherwise the bookkeeping and the bloat/UAF risk cost more than the default allocator.

---

## Data-Structure Memory Efficiency — Layout, SoA, and Interning

How much memory a structure uses, and how fast it is to traverse, is often decided by *layout*, not by the algorithm.

- **Struct padding and alignment.** The compiler inserts padding so each field meets its alignment requirement, and rounds the struct up to its largest field's alignment. Field *order* therefore changes size:

```go
type Bad  struct { a bool; b int64; c bool }   // 1 + 7pad + 8 + 1 + 7pad = 24 bytes
type Good struct { b int64; a bool; c bool }   // 8 + 1 + 1 + 6pad     = 16 bytes
// 33% smaller, same fields — order largest-to-smallest to minimize padding.
```

- At scale this compounds: 24 vs 16 bytes across 100M records is 800 MB vs 1.6 GB, and the smaller layout fits more records per cache line. Tools: Go `fieldalignment` (in `go vet`), Rust `#[repr(C)]` + manual ordering, C `pahole` (shows holes in any struct).
- **Array of Structs vs Struct of Arrays (AoS vs SoA).** AoS stores records contiguously (`[]Point{{x,y,z}, ...}`); SoA stores each field in its own array (`xs []float64; ys []float64; zs []float64`).
  - When you process *one field across all records* (sum all `x`s, filter by one column), SoA is dramatically faster: it brings only the needed field into cache (no wasted bytes on `y`/`z`) and lets the CPU vectorize. This is the entire premise of **columnar** storage (Arrow, Parquet, ClickHouse, vectorized query engines) — column-at-a-time scans with SIMD over dense, same-type runs.
  - AoS wins when you touch *whole records* (random access to one object's all fields).
- **Interning and compression.** When a value space is small but repeated billions of times, store each distinct value once.
  - **String interning** replaces N copies of `"us-east-1"` with one shared instance referenced by index — turning a string column into a dictionary + small integer codes (dictionary encoding, again a columnar staple).
  - For numeric columns, delta/run-length/bit-packing encodings shrink memory and improve scan speed because more values fit per cache line. The general principle: *the cheapest byte is the one you never store* — exploit redundancy in the data's value distribution, not just its allocation pattern.

> **Key insight:** Memory efficiency is mostly layout and redundancy, decided before the first allocation. Reorder fields to kill padding; choose SoA/columnar when access is field-at-a-time; intern and encode when the value distribution is skewed. These change the *constant factor* on every record, which at scale beats almost any allocator tweak.

---

## Off-Heap and mmap for Huge Datasets

When a dataset is larger than you want resident — or larger than RAM — the answer is to stop treating it as heap objects and let the OS page it for you.

- **`mmap` for huge read-mostly datasets.** Mapping a file into the address space makes the OS page cache your memory manager: pages fault in on first touch, and the kernel evicts cold pages under pressure (file-backed clean pages cost nothing to evict — no swap write).
  - You can map a 200 GB index into a process with 16 GB of RAM and touch it as if it were an array; only the hot pages stay resident. This is how LMDB, many search indexes, and memory-mapped model weights work.
  - The cost is that access patterns now matter enormously — a random walk over a memory-mapped dataset is a storm of page faults, and the OS, not you, decides what stays.

```c
int fd = open("index.dat", O_RDONLY);
void *p = mmap(NULL, len, PROT_READ, MAP_PRIVATE, fd, 0);
madvise(p, len, MADV_RANDOM);     // tell the kernel: don't readahead, access is random
// ... treat p as an array; pages fault in lazily, evict under pressure ...
```

- **Off-heap for GC avoidance.** In managed runtimes, the second reason to go off-heap is to hide data from the collector entirely. A 100 GB on-heap cache forces the GC to scan 100 GB of pointers every cycle, even if nothing changes; moving it off-heap (direct `ByteBuffer`s, the FFM API, or a serialized blob in `mmap`'d memory) makes it *GC-invisible* — the collector sees one handle, not a billion entries. The trade is the one custom allocation always makes: you reclaim manual-memory risk in exchange for not paying GC scan cost.
- **Measuring it all.** None of this off-heap memory shows up in a *heap* profiler — which is exactly why "the heap profile says 900 MB but the process is using 8 GB" is the signature of an off-heap-heavy program. The accounting must come from the OS:

```bash
cat /proc/$PID/smaps_rollup        # Rss, Pss; file-backed (mmap) vs anon (heap/off-heap)
pmap -x $PID                        # per-mapping RSS — find the big mmap'd files
GODEBUG=gctrace=1 ./app | ...       # Go: compare HeapInuse to process RSS
jcmd $PID VM.native_memory summary  # JVM NMT: heap vs metaspace vs direct vs thread stacks
```

> **Key insight:** Past a certain size, the OS is a better memory manager than your allocator or GC, and `mmap` is how you delegate to it. The decision point: data too big for RAM, or too big to let the GC scan → push it off-heap / `mmap` it, accept that access patterns and manual lifetime now dominate, and *measure footprint from the OS*, because no heap profiler will ever see it.

---

## Common Mistakes

1. **Treating RSS and live heap as the same number.** They diverge via fragmentation, unreturned pages, and off-heap mappings. A heap profiler explains live heap only; for the rest you need `smaps`, allocator stats, and NMT/gctrace. Conflating them sends you optimizing the wrong layer.
2. **Tuning `GOGC` to fight OOM-kills in a container.** `GOGC` is a *ratio* and can't bound absolute memory — a growing live set still blows the limit. Use **`GOMEMLIMIT`** as the absolute backstop and leave `GOGC` at default for steady-state efficiency.
3. **Reaching for `sync.Pool` (or any pool) without a profile showing allocation/GC pressure.** Pools add reset-bug and bloat risk (a variable-size pool retains the largest object forever). They pay off only when construction is expensive or allocation rate is genuinely pressuring the GC.
4. **Picking a low-pause collector (ZGC/Shenandoah) for a throughput batch job.** Their read/relocation barriers and headroom cost throughput you don't need to spend. Match the collector to the SLO: G1 or a throughput collector for batch; ZGC/Shenandoah only when pauses must stay flat as the heap grows.
5. **Using an arena where lifetimes aren't batch-scoped.** Arenas can't free individual objects; one long-lived object pins the whole arena. They fit phase-scoped lifetimes (request, pass, frame) and nothing else.
6. **Ignoring struct field order at scale.** Padding silently inflates per-record size 20–50%. Order fields largest-to-smallest (or run `fieldalignment` / `pahole`); across 100M records the difference is gigabytes.
7. **Profiling only the heap on an off-heap-heavy program.** Direct buffers, `mmap`, metaspace, thread stacks, and JIT caches are all in RSS and invisible to a heap profiler. When heap profile ≪ RSS, the memory is non-heap — measure it from the OS (`smaps`, `pmap`, NMT).

---

## Apply it

1. State the system invariant that **Memory and Allocation Optimization** must protect.
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

- Which invariant must remain true when Memory and Allocation Optimization fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
- Explain tracing vs reference-counting garbage collection, and what "generational" and "concurrent" each add.
- Contrast the JVM's G1 and ZGC collectors. When would you pick each?
- What is fragmentation, which collectors suffer from it, and why does Go tolerate it?
- In a heap profile, what's the difference between `inuse_space`, `alloc_space`, `inuse_objects`, and `alloc_objects`?
- RSS keeps climbing but live heap is flat — what's happening, and how would you find the cause?
- A long-running service slowly degrades over days until it's restarted. Is this memory-related, and how would you confirm it?
- Latency p99 spikes correlate with GC cycles, but mean latency is fine. What's happening, and how do you fix it?
