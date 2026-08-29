# Tracing Garbage Collection — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Tracing Garbage Collection** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Allocation in a GC'd Heap

Allocation speed matters as much as collection speed, because allocation happens far more often. Modern runtimes make the common case nearly free:

- **Bump-pointer allocation:** in a contiguous region (a copying nursery, a TLAB), allocating an object is "read the bump pointer, add the size, check the limit, store the new pointer." A handful of instructions, no search. This is why generational collectors with copying nurseries allocate so fast — and why fragmentation (which breaks contiguity) is so costly.

- **TLABs:** if every thread bumped the *same* global pointer, allocation would need an atomic op or lock and would contend badly. Instead each thread owns a **TLAB** — a private chunk of the nursery — and bump-allocates inside it with no synchronization. When the TLAB fills, the thread atomically grabs a fresh one. HotSpot, V8, and .NET all use TLABs; Go uses per-P (per-processor) `mcache` spans serving the same role.

- **Escape analysis & stack allocation:** the cheapest GC'd allocation is the one that never hits the heap. If the compiler proves an object can't outlive its function (doesn't *escape*), it allocates it on the stack — zero GC cost. Go leans heavily on this in lieu of a generational nursery; the JVM does scalar replacement under C2. `go build -gcflags=-m` shows escape decisions.

**Practical consequence:** the single most effective GC optimization is usually *allocating less* (or allocating on the stack), not tuning the collector. Fewer, larger, longer-lived allocations and reused buffers beat any flag.

## The Cost Model: What You Actually Pay

A tracing GC charges you on four meters simultaneously:

1. **Pause time (latency):** wall-clock time mutators are stopped. Concurrent collectors shrink this to root-scan + barrier-flip time; STW collectors pay marking + moving time.
2. **Throughput overhead (CPU):** marking, sweeping, copying, *plus* the barrier tax on every relevant pointer write (and read, for load-barrier collectors). Typically 5–25% of CPU in busy services.
3. **Memory overhead (footprint):** headroom for concurrent collection, plus per-object headers/mark bits, plus (for copying/semispace) the reserved half. A concurrent collector that runs at 2× live set isn't misconfigured — it's buying latency with RAM.
4. **Floating garbage:** memory held one cycle longer than necessary (worse under SATB).

These trade against each other. Lowering pauses (more concurrency, more frequent collection) costs throughput and memory. Lowering memory (collect more aggressively) costs throughput. **Tune the meter your SLO cares about, and explicitly accept the cost on the others.**

## Pause Analysis

When latency spikes correlate with GC, decompose the pause rather than guessing:

- **Is it actually GC?** Correlate latency outliers with GC events (Go: `GODEBUG=gctrace=1`, runtime traces; JVM: GC logs, JFR). A "GC pause" on the dashboard might be CPU starvation, page faults, or a noisy neighbor — confirm before tuning.

- **Decompose the STW.** Even concurrent collectors have small STW phases. Separate:
  - **Time-to-safepoint (TTSP):** how long until all threads stopped. A large gap between "GC requested" and "all stopped" means a thread is stuck off-safepoint (a long counted loop, a JNI critical section, a syscall) — fix the code, not the collector.
  - **Root scanning / barrier flip:** usually tiny and fixed-ish.
  - **Concurrent phases:** run alongside mutators; they cost CPU and can starve the app if the machine is saturated.

- **Watch for fallbacks.** The worst pauses are *concurrent-mode failures*: the mutator out-allocated the collector, forcing a STW full collection.
  - Go: mutators get conscripted into **GC assist**, which manifests as latency on the allocating goroutine, not a global pause — but it *feels* like a slowdown.
  - JVM (G1): **to-space exhausted** / **evacuation failure** triggers a full GC. CMS (legacy) had **concurrent mode failure**. These are the multi-hundred-ms outliers.

- **Distinguish frequency from duration.** Many short pauses (high allocation rate → frequent young GC) vs few long pauses (large heap → long old GC) call for opposite fixes. Pull both *pause duration distribution* and *pause frequency* before acting.

## Pacing, Headroom, and the Key Knobs

### Go

- **`GOGC`** (default 100): the central knob. `GOGC=100` means "start the next GC when the heap has grown 100% beyond the live set after the last GC" — i.e., collect when heap ≈ 2× live. Higher `GOGC` (e.g., 200, 400) → fewer collections, **more throughput, more memory**; lower (e.g., 50) → more frequent collections, **less memory, more CPU**. `GOGC=off` disables GC (for short-lived batch processes only).

- **`GOMEMLIMIT`** (Go 1.19+): a soft memory ceiling. The pacer becomes more aggressive as the heap approaches the limit, regardless of `GOGC`. This is the modern way to run in a container: set `GOMEMLIMIT` to ~the container memory limit (minus headroom) to avoid OOM-kills, and keep `GOGC` for the steady state. Using both is the recommended pattern — `GOMEMLIMIT` as a safety net, `GOGC` for normal pacing.

- **The pacer** tries to finish marking exactly as the heap hits the trigger, scheduling background mark workers and, if the app allocates too fast, **GC assists** to keep the mutator from outrunning the collector. Observe with `GODEBUG=gctrace=1` (per-cycle line: wall/CPU time, heap sizes) and `runtime/metrics` (`/gc/...`).

- **No generations, non-moving:** Go has no young/old knobs. You reduce GC cost by reducing allocation (escape analysis, `sync.Pool` for hot short-lived objects, preallocated/reused buffers, fewer pointers per object to shrink scan time).

### HotSpot JVM

- **Pick the collector first.** `-XX:+UseG1GC` (default), `-XX:+UseZGC` (+ `-XX:+ZGenerational` for the generational mode), `-XX:+UseShenandoahGC`, `-XX:+UseParallelGC` (throughput). This choice dominates all other tuning.

- **Heap sizing:** `-Xms`/`-Xmx` (set equal in servers to avoid resize pauses). For low-latency collectors, **provision headroom** — running ZGC at 90% of heap defeats it.

- **Pause-time goal (G1):** `-XX:MaxGCPauseMillis=200` — G1 sizes its collection set to *try* to meet this. It's a goal, not a guarantee; setting it absurdly low (e.g., 5 ms) just makes G1 collect tiny slices constantly, hurting throughput.

- **Generation sizing (where applicable):** `-XX:NewRatio`, `-XX:SurvivorRatio`, `-XX:MaxTenuringThreshold` control nursery size and promotion. Bigger young gen → fewer, larger minor GCs and less premature promotion; too big → longer minor pauses and a smaller old gen.

- **Observability:** unified logging `-Xlog:gc*:file=gc.log:time,uptime,level,tags`, **JFR** (`-XX:StartFlightRecording`), and tools like GCViewer/GCeasy to visualize pause distribution, allocation rate, and promotion rate. async-profiler attributes allocations to call sites.

## Diagnosing GC Problems

A repeatable playbook:

1. **Confirm GC is the cause.** Correlate latency tail with GC events; rule out CPU saturation, paging, lock contention, and downstream calls first.
2. **Pull the four meters.** Allocation rate, promotion rate, pause distribution (count + duration percentiles), and live-set/heap-size trend.
3. **Find the dominant cost.** High allocation rate → attack allocation (the usual culprit). Rising live set over time → a **leak** (retained references); the GC can't fix what's still reachable. Long old-gen pauses with low allocation → heap too small or fragmentation.
4. **Attack allocation before flags.** Profile allocations (pprof `alloc_space`/`inuse_space`; JFR allocation events). Eliminate hot allocation sites: stack-allocate, pool, reuse buffers, avoid boxing, pick better data structures (struct-of-arrays, fewer pointers).
5. **Then tune pacing/headroom.** Adjust `GOGC`/`GOMEMLIMIT` or `-Xmx`/pause goal/collector. Change *one* variable, measure under representative load, keep or revert.
6. **Validate at the tail.** GC wins or losses show in p99/p99.9, not p50. Always read tail percentiles under production-like load.

## Coding Patterns

- **Reduce allocation rate.** Reuse buffers (`bytes.Buffer`, preallocated slices with `make([]T, 0, n)`), avoid per-request allocations in hot paths, and let escape analysis keep temporaries on the stack.
- **`sync.Pool` (Go) / object pools — with discipline.** Effective for high-churn, uniform, short-lived objects (e.g., per-request scratch buffers). They add complexity and bugs (stale state, retained references); pool only what the allocation profile flags, and reset objects on `Put`.
- **Shrink object graphs the collector must scan.** Fewer pointer fields → faster marking. Prefer value types/arrays over linked structures of small heap objects where it fits the access pattern.
- **Avoid retention leaks.** Unbounded caches/maps, slices aliasing huge backing arrays (`s = s[:0]` keeps the backing array; reslice or copy to release), and goroutine/closure captures of large objects keep memory reachable forever — the GC is powerless.
- **Batch and right-size.** Allocate a few large buffers instead of many small ones; size collections up front to avoid growth churn.

## Best Practices

- **Set `GOMEMLIMIT` (or `-Xmx`) to the container limit minus headroom.** Match the runtime's view of memory to its cgroup; an unaware runtime OOM-kills or thrashes.
- **Provision headroom for concurrent collectors.** They need room to allocate *during* a cycle; starving them forces STW fallbacks — the very outliers you were avoiding.
- **Pick the collector for the SLO, then leave defaults mostly alone.** Modern defaults (G1, Go's pacer) are good; most teams improve latency far more by cutting allocation than by twiddling flags.
- **Keep GC observability on in production.** Lightweight GC tracing/JFR is cheap insurance; you cannot diagnose what you didn't record.
- **Load-test at production scale before tuning.** GC behavior is wildly nonlinear in allocation rate and live-set size; micro-benchmarks mislead.

## Edge Cases & Pitfalls

- **Container-unaware runtimes:** an old JVM/Go binary that reads host RAM, not the cgroup limit, sizes its heap for the whole machine and gets OOM-killed. Set memory limits explicitly.
- **Pause-goal that's too aggressive:** `MaxGCPauseMillis=1` makes G1 thrash with constant tiny collections and tanks throughput. Set realistic goals.
- **`GOGC` too high in memory-constrained pods:** fewer collections feel faster until the pod OOM-kills. Pair with `GOMEMLIMIT`.
- **Mistaking a leak for a tuning problem:** if the live set grows monotonically, no flag will help — you have retained references. Heap-profile and fix the retention.
- **Slice/substring aliasing:** holding a small slice of a giant array (or a substring of a huge string in languages where that aliases) pins the whole backing store. Copy out the small part.
- **GC assist masquerading as random slowness:** in Go, allocation-heavy goroutines doing assist work look like sporadic latency on *those requests*, not a global pause — easy to misattribute.
- **Promotion-rate spikes:** bursty traffic promotes short-lived objects, then a major GC must reclaim them — pauses correlate with *yesterday's* allocation burst, not current load.

---

## Apply it

1. Define the user or business outcome that **Tracing Garbage Collection** should improve.
2. Assign one owner for code, contracts, operations, and incidents.
3. Split delivery into reversible increments that produce evidence early.
4. Publish responsibilities, escalation paths, and compatibility windows.
5. Stop or expand only when the agreed measures support that decision.

## Verify your work

- Each increment has an owner, rollback path, and observable exit condition.
- Adoption, reliability, delivery time, and coordination cost are measured.
- Incident and migration exercises prove that responsibility is executable.
- The old path is removed only after telemetry proves it is unused.

## Review questions

- Which measurable outcome justifies investing in Tracing Garbage Collection?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
