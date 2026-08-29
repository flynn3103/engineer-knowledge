# Allocation Profiling — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Allocation Profiling** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Profiling](../README.md) → Allocation Profiling
> *The middle page taught you to read `-alloc_space` and spot a string-concatenation hot spot. This page is about the machinery underneath: the Poisson sampler that makes `alloc_space` an estimate, the unsampling math that scales it back to a number you can trust, the quantitative link from allocation rate to GC CPU and pause time, and escape analysis as the root cause every allocation profile is silently pointing at.*

---

## How Go Samples Allocations — MemProfileRate and the Poisson Sampler

A naive allocation profiler would record a stack trace on *every* `malloc`. In a service allocating a million objects per second that is unaffordable — the profiling overhead would dwarf the workload. Every production allocation profiler therefore **samples**, and to use the output correctly you have to know exactly *how*.

Go's heap profiler is controlled by one knob:

```go
runtime.MemProfileRate = 512 * 1024   // the default: 512 KiB
```

The documented contract is "profile approximately one allocation for every `MemProfileRate` bytes allocated." The word *approximately* is doing real work. Go does **not** sample deterministically every 512 KiB — that would alias badly against any allocation pattern whose stride is a multiple of the rate (imagine a loop that allocates exactly 512 KiB per iteration; deterministic sampling would credit one call site and miss everything else). Instead the runtime draws each sample interval from an **exponential distribution** with mean `MemProfileRate`. Because allocations arrive as a stream and the *gaps between sampled allocations* are exponential, the sampling process is a **Poisson process** over the byte stream — the continuous-allocation analog of "flip a weighted coin per byte."

Mechanically, the runtime keeps a per-P countdown of bytes until the next sample (`mcache.nextSample`). Each allocation decrements it by the object's size; when it crosses zero, the runtime records a stack trace for *that* allocation and redraws the next interval from the exponential distribution (`fastexprand` in the runtime). The redraw is the crucial part: a fresh exponential gap each time is what guarantees every allocation has probability proportional to its size of being the one sampled, with no aliasing.

```go
// Conceptually, per allocating goroutine's P:
nextSample -= size
if nextSample <= 0 {
    record_stack_for_this_allocation()
    nextSample = exponential_draw(mean = MemProfileRate)
}
```

The size-weighting falls out for free and is the reason `-alloc_space` and `-alloc_objects` are *different questions* answered by the *same samples*. A 4 MiB allocation crosses the countdown far more often than a 64-byte one — so large allocations are over-represented per object but correctly represented per byte. When you ask for `alloc_space`, pprof reports the size-weighted estimate; when you ask for `alloc_objects`, it reports the count estimate. A call site that does `make([]byte, 8<<20)` once dominates `alloc_space` and is invisible in `alloc_objects`; a call site that does `make([]byte, 64)` ten million times is the reverse. **Reading the wrong one is the single most common way seniors misdiagnose an allocation problem.**

```bash
# Both views come from the same heap profile:
go tool pprof -alloc_space   ./bin cpu.heap   # bytes — "what's churning the most memory?"
go tool pprof -alloc_objects ./bin cpu.heap   # count — "what's churning the most objects?"
```

Tuning the rate is a real lever. `MemProfileRate = 1` records *every* allocation (exact, but expensive — only for short benchmark runs). Setting it to `0` disables heap profiling entirely. Doubling it from 512 KiB to 1 MiB halves the sample volume and the overhead, at the cost of resolution on rare-but-large call sites. Note one sharp edge: `MemProfileRate` must be set **before any allocation you care about happens** — set it in an `init()` or at the very top of `main`, because the runtime captures the value when it first arms the sampler.

> **Key insight:** `-alloc_space` is not a measurement, it is an **estimate from a Poisson sampler**. The exponential redraw per sample is what makes it size-proportional and alias-free, which is *also* what makes `-alloc_space` and `-alloc_objects` two valid answers to two different questions from one set of samples. Know which question you're asking before you read the graph.

---

## Unsampling — Why alloc_space Is an Estimate and How It's Scaled Back

If the profiler only recorded one allocation per ~512 KiB, how does pprof report "this call site allocated 4.2 GB"? It **unsamples** — it scales each sample back up to estimate the population it represents. Getting this math is what separates "the graph says 4 GB" from "I trust the 4 GB."

When the runtime records a sample at an allocation of size `s`, with rate `R = MemProfileRate`, the probability that *this particular allocation* was the one to trip the countdown is approximately `s / R` for small objects (each byte has ~`1/R` chance; `s` bytes, so ~`s/R`). The unbiased estimator therefore multiplies each sample by the inverse of its sampling probability:

```
scale(size) ≈ 1 / (1 - exp(-size / R))
```

That `1 - exp(...)` form (not the naive `R/size`) is the exact correction Go's runtime uses — it stays accurate even when an object's size is large relative to `R`, where the simple `R/size` approximation breaks down. For a small object (`size ≪ R`), `1 - exp(-size/R) ≈ size/R`, so the scale is ≈ `R/size` — a 64-byte sample with `R = 512 KiB` stands in for ~8192 such objects. For a huge object (`size ≫ R`), the scale approaches `1` — a 16 MiB allocation is almost certainly sampled every time, so it represents essentially just itself.

```go
// Runtime's scaling, conceptually (see runtime/mprof.go scaleHeapSample):
func scale(count, size, rate int64) (int64, int64) {
    if rate <= 1 { return count, size }            // every alloc recorded; no scaling
    if count == 0 { return 0, 0 }
    avgSize := float64(size) / float64(count)
    scale  := 1 / (1 - math.Exp(-avgSize/float64(rate)))
    return int64(float64(count) * scale),
           int64(float64(size)  * scale)
}
```

Three consequences a senior must internalize:

1. **The estimate has variance, and the variance is worst exactly where the data is thinnest.** A call site with thousands of samples is tight; a call site that produced *two* samples is a coin-flip estimate that pprof will still print to the byte. Treat small-sample call sites as order-of-magnitude, not exact. If you need precision on a specific path, lower `MemProfileRate` for a targeted run.

2. **`alloc_*` is cumulative since process start; `inuse_*` is a snapshot.** The heap profile carries four columns — `alloc_objects`, `alloc_space`, `inuse_objects`, `inuse_space`. The `alloc_*` pair is *everything ever allocated* (the churn — what this section cares about); the `inuse_*` pair is *what survived the last GC* (retention — that's [Memory Profiling](../02-memory-profiling/senior.md)). Same samples, but `inuse` is computed by walking which sampled objects are still reachable. Confusing them sends you optimizing churn when you have a leak, or vice versa.

3. **The number is only as good as the rate it was taken at.** Two profiles taken at different `MemProfileRate` values are both unbiased estimates of the same truth, but with different variance. When you compare before/after (next section), keep the rate identical or you are comparing estimators with different noise floors.

> **Key insight:** pprof's `alloc_space` total is a *reconstructed population estimate*, `sampled_bytes × 1/(1−e^(−size/R))`, not a tally. That's why it's trustworthy in aggregate (millions of samples average out) and noisy per-call-site when samples are few — and why the very-large and very-small object regimes scale by completely different factors.

---

## JVM Allocation Sampling — TLAB Boundaries, JFR, and async-profiler

The JVM samples allocations too, but the mechanism is tied to a different runtime structure: the **TLAB** (Thread-Local Allocation Buffer). Understanding TLABs explains both *why* JVM allocation sampling is nearly free and *what it systematically misses*.

The fast path of a Java `new` is a **pointer bump** inside the thread's TLAB — a private chunk of Eden the thread carved out so it can allocate without any cross-thread synchronization. The thread just increments a pointer; there is no lock, no CAS, no runtime call. This is why allocation in Java is famously cheap (a handful of instructions) — and it's exactly why you *can't* cheaply instrument every allocation: the common path never enters the runtime at all.

So the JVM piggybacks its sampling on the *one moment the allocation slow path runs*: when the TLAB is exhausted. Historically this surfaced as two JFR events:

- **`jdk.ObjectAllocationInNewTLAB`** — fired when an allocation didn't fit the current TLAB and the thread grabbed a fresh one. This is the implicit sampler: you get one event roughly per TLAB-worth of allocation (TLABs are adaptively sized, often tens to hundreds of KiB), so the *effective sample rate is "one per TLAB refill,"* not one per allocation.
- **`jdk.ObjectAllocationOutsideTLAB`** — fired for allocations too large to fit any TLAB, allocated directly in the heap (the "humongous"/large-object path). These are individually significant and always recorded.

The trouble with TLAB-boundary sampling is that its bias is *structural and hard to reason about*: the event fires on the allocation that *happened to overflow the TLAB*, which is not necessarily the call site responsible for most of the bytes — it's whoever drew the short straw at the boundary. The sample rate is also coupled to TLAB sizing, which the JVM tunes adaptively per thread.

JDK 16+ replaced this with **`jdk.ObjectAllocationSample`** (JEP 349), a properly rate-limited sampler that targets a *maximum event rate* (a small, bounded number of samples per second regardless of allocation pressure) and reports an estimated `weight` per sample so you can unsample back to bytes — the same statistical idea as Go, but rate-limited by *events per second* rather than *bytes per sample*. This is the event you want in modern JFR: bounded overhead, no TLAB-coupling, and a weight field for scaling.

```bash
# Modern JFR: low-overhead, rate-limited allocation sampling
java -XX:+FlightRecorder \
     -XX:StartFlightRecording=settings=profile,filename=app.jfr MyApp
# Then read jdk.ObjectAllocationSample events:
jfr print --events jdk.ObjectAllocationSample app.jfr
```

**async-profiler `--alloc`** takes a sharper approach. Instead of (or in addition to) JFR events, it installs a callback on the JVM's TLAB-allocation and outside-TLAB code paths via the internal `AsyncGetCallTrace` / TLAB hooks, samples at a configurable byte interval (`--alloc 512k`), and — critically — captures the **full native + Java call stack** at the allocation point, including frames the JFR events flatten. That stack fidelity is why async-profiler allocation flame graphs are usually more actionable than raw JFR allocation views.

```bash
# Sample one allocation per ~512 KiB, emit a flame graph:
asprof -e alloc -i 512k -f alloc-flame.html <pid>
```

> **Key insight:** Java allocation is a TLAB pointer-bump, so the runtime only "sees" allocations at TLAB boundaries — which is why pre-JDK-16 allocation profiling sampled *one event per TLAB refill* with a bias toward whoever overflowed the buffer. `jdk.ObjectAllocationSample` (JEP 349) and async-profiler's `--alloc` both replace that with a rate-controlled sampler plus a per-sample weight, mirroring Go's unsampling idea on a completely different allocation mechanism.

---

## The Alloc-Rate / Heap / Pause Triangle

Here is the reason allocation profiling earns its place at all. You don't reduce allocations because allocations are intrinsically bad — short-lived stack-like objects are nearly free. You reduce them because **allocation rate drives GC frequency, and GC frequency drives CPU and pause cost.** A senior reasons about this quantitatively, not as folklore.

Take a tracing collector with a heap that grows from a live set `L` up to a trigger size before collecting. In Go that trigger is governed by `GOGC` (default 100): the GC runs when the heap reaches `L × (1 + GOGC/100)` — i.e., when *new allocation since the last GC* equals the live set. So the **headroom** between collections is:

```
headroom = L × (GOGC / 100)        # default GOGC=100 → headroom = L (one live-set's worth)
```

If your steady-state live set is `L = 200 MB` and `GOGC = 100`, the GC fires every time you allocate another 200 MB. Now bring in allocation rate `A` (bytes/sec from your profile):

```
GC_period   = headroom / A = (L × GOGC/100) / A
GC_freq     = A / (L × GOGC/100)            # collections per second
```

At `A = 2 GB/s` and headroom `200 MB`, that's a GC **every 100 ms — 10 collections per second.** Halve the allocation rate to `1 GB/s` (the thing your allocation profile lets you do) and you get a GC every 200 ms — **GC frequency halved, with no change to the heap or the live set.** That is the entire payoff of allocation reduction expressed in one equation.

The three corners trade off against each other:

- **Lower allocation rate `A`** → fewer GCs → less GC CPU. *This is what allocation profiling buys you.*
- **Larger heap headroom (raise `GOGC`, or `-Xmx`)** → fewer GCs → less GC CPU, **but** more RAM and a larger live region to scan, which can grow pause time in non-concurrent or partially-concurrent phases.
- **Pause/latency target** (Go's soft goal, `MaxGCPauseMillis` for G1) → the collector does more concurrent work and may collect *more often* to hit the target, raising CPU.

You cannot optimize all three at once; you pick the constraint that's binding. GC **CPU cost** scales with how much you scan, ≈ `GC_freq × (cost to mark the live set)` ≈ `(A / headroom) × c·L`. Two ways to cut it: shrink `A` (allocation profiling) or grow headroom (more RAM). They trade memory for CPU against each other — and the allocation profile tells you whether the `A` lever even *has* room to move.

```bash
# Watch the triangle live in Go:
GODEBUG=gctrace=1 ./app
# gc 47 @8.123s 4%: 0.18+12+0.21 ms clock, ...  4->210->105 MB, 210 MB goal, ...
#   "4%"            → fraction of CPU spent in GC  (the cost you're managing)
#   "210 MB goal"   → the trigger = live × (1+GOGC/100)
#   heap 4->210->105 → before / peak / after; (210-4) over the period = A × period
```

> **Key insight:** Allocation reduction is GC-frequency reduction at **constant heap**. With Go's `GOGC=100`, GC frequency ≈ `A / live_set` — so halving the allocation rate from your profile halves GC frequency and roughly halves GC CPU *for free*, where "raise GOGC" would have bought the same CPU only by spending more RAM. The profile tells you which lever is available.

---

## Escape Analysis — The Root Cause the Profile Points At

An allocation profile tells you *where* heap allocations happen. It almost never tells you the *why* — and the why, in a compiled GC'd language, is nearly always **escape analysis deciding a value must live on the heap.** The senior workflow is: profile points at a call site → open the escape-analysis report → understand *why* the compiler heap-allocated → remove the reason. The profile is the symptom; escape analysis is the diagnosis.

Escape analysis is the compiler pass that asks, for each value: *does its lifetime provably end when the function returns?* If yes, it goes on the stack (freed for free when the frame pops, invisible to the GC, never in your allocation profile). If the compiler **can't prove** the lifetime is bounded — the value's address outlives the frame — it must "escape" to the heap. Crucially this is a *conservative* analysis: when in doubt, it heap-allocates. Most removable allocations are cases where the value *could* have stayed on the stack but the compiler couldn't prove it.

Read the report directly:

```bash
go build -gcflags='-m' ./...        # one -m: the decisions
go build -gcflags='-m -m' ./...     # two -m: WHY each decision was made (the reasoning chain)
```

```go
func leak() *int {
    x := 42
    return &x          // -m: "moved to heap: x"  — address outlives the frame, must escape
}

func stays() int {
    x := 42
    return x           // no escape: x lives and dies on the stack, never in the profile
}
```

The canonical escape triggers — the ones your profile will keep pointing at:

- **Returning a pointer to a local.** The address outlives the frame; classic escape.
- **Storing a pointer in something that escapes** — a struct field, a slice/map element, a global. The local is now reachable from outside.
- **Interface conversion.** Putting a concrete value into an `interface{}` (or any interface) usually forces it to the heap, because the interface holds a pointer and the compiler often can't bound the interface's lifetime. `fmt.Println(x)` boxes `x` to satisfy `...interface{}` — a leading cause of "mysterious" allocations in logging-heavy code. (Go's small-int and some constant cases are optimized, but the general rule holds.)
- **Closures capturing by reference.** A closure that captures `&x` (or mutates a captured variable) forces `x` to the heap so the closure can outlive the frame.
- **Slices/maps whose size the compiler can't bound.** `make([]T, n)` with non-constant `n` escapes; `make([]T, 8)` with a constant small size can stay on the stack.

Three deeper interactions a senior must hold:

**Inlining changes escape outcomes.** Escape analysis runs *after* inlining, and inlining is what makes many small-value optimizations possible — once a callee is inlined into its caller, the compiler can see that the "returned pointer" never actually leaves the combined frame and keep it on the stack. This is why a function that allocates when called normally may *stop* allocating once it's small enough to inline, and why bumping a function over the inlining budget (it gets too big, e.g., by adding a `defer` or growing past the cost threshold) can silently *introduce* heap allocations at call sites that were previously stack-only. Check with `-gcflags='-m=2'`, which also prints inlining decisions.

**Interface devirtualization.** When the compiler can prove the concrete type behind an interface call (a monomorphic call site), it can *devirtualize* — replace the dynamic dispatch with a direct call, which then opens the door to inlining and *that* can let the value stay on the stack. Hidden polymorphism (passing values through `interface{}` you could have kept concrete) defeats this and shows up as allocation in the profile.

**`sync.Pool` is the escape hatch for allocations you couldn't eliminate.** When a value genuinely must escape (it's large, or its lifetime legitimately crosses the frame) and the call site is hot, `sync.Pool` lets you *recycle* the heap object instead of allocating a fresh one each time — amortizing the allocation across many uses. It doesn't make the allocation go away in the profile the first time, but it collapses the steady-state rate. Critically, a pooled object's lifetime is now *your* responsibility: it must be fully reset on `Put` (stale data is a classic pool bug), and the pool is cleared every GC, so it only helps for high-churn, short-lived reuse. The *techniques* for applying pools belong to [optimization](../../05-memory-and-allocation-profiling/senior.md) — here the point is that the profile + escape report is how you decide *which* call site deserves a pool.

> **Key insight:** Every line in your allocation profile is an escape-analysis verdict. `-gcflags='-m -m'` turns the profile's *where* into a *why* — and the why is almost always one of a handful of triggers (returned pointer, interface boxing, unbounded `make`, by-reference capture) that you can often remove by keeping the value concrete, bounding a size, or letting inlining do its job.

---

## Differential Allocation Profiles — Proving a Fix

A senior never claims an optimization worked because "the flame graph looks better." You prove it with a **differential (before/after) profile** — and you control for the sampler so you're measuring the fix, not the noise.

The pattern in Go: capture a profile before the change, capture one after under the *same* load and the *same* `MemProfileRate`, and diff them.

```bash
# Baseline and candidate, identical rate and workload:
go test -run=XXX -bench=BenchHot -memprofile=before.heap -benchmem
# ... apply the fix ...
go test -run=XXX -bench=BenchHot -memprofile=after.heap  -benchmem

# Diff: -base subtracts the baseline; positive = added by the fix, negative = removed
go tool pprof -alloc_space -base=before.heap after.heap
go tool pprof -alloc_objects -base=before.heap after.heap   # check BOTH views
```

The `-base` flag subtracts sample-for-sample, so the flame graph now shows *deltas*: a call site you fixed shows as a large negative contribution, and — just as important — you can *see if your fix pushed allocations somewhere else* (a positive delta you didn't expect). Diffing both `-alloc_space` and `-alloc_objects` catches the case where you cut total bytes but tripled object count (e.g., you replaced one big buffer with many small ones), which can *worsen* GC because the collector cost is partly per-object, not purely per-byte.

For microbenchmarks, `-benchmem` gives you the per-operation ground truth that the sampled profile can only estimate:

```
BenchHot-8   1.2µs/op   512 B/op   3 allocs/op     # before
BenchHot-8   0.4µs/op     0 B/op   0 allocs/op     # after — provably zero-allocation
```

`allocs/op` and `B/op` here are **exact** (the benchmark framework counts with `runtime.ReadMemStats` deltas around the measured loop, not sampling), which makes them the gold standard for "did this path become allocation-free?" Use the sampled profile to *find* the path; use `-benchmem` on a focused benchmark to *prove* the fix to the byte and to guard it against regression in CI.

On the JVM, the same discipline applies with JFR: record `jdk.ObjectAllocationSample` before and after, and diff the per-class / per-stack allocation totals (`jfr print` plus your own aggregation, or a JMC/async-profiler diff view).

> **Key insight:** A real allocation fix is proven by a *differential* profile under controlled load and an identical sample rate, cross-checked on both bytes and objects, and pinned by an exact `-benchmem`/`allocs/op` assertion in a benchmark — so the win is measured, attributed, and regression-guarded, not eyeballed.

---

## The Subtle Cases — Misattribution, Runtime-Internal, Conversions

The flame graph lies in specific, knowable ways. A senior recognizes these patterns instead of chasing them.

**Inlining misattributes the line.** Because escape analysis and attribution happen after inlining, the allocation can be credited to the *inlined-into* function rather than the source line you'd expect. A helper that allocates, once inlined, shows the allocation at the call site, not inside the helper — so "this line allocates and I don't see why" is often "an inlined callee allocated here." Build with `-gcflags='-m=2'` to see the inlining, and read the profile with that map in hand. (pprof's source view, `list <func>`, helps line this up.)

**Runtime-internal allocations have no obvious source line.** A large fraction of allocations in a real Go service come from the *runtime*, not your `new`/`make`:

- **Map growth / rehash.** A `map` that grows past its load factor reallocates its bucket array; a map you didn't pre-size with `make(map[K]V, n)` rehashes repeatedly as it fills, each rehash a runtime allocation attributed to `runtime.mapassign`/`runtime.growslice`-adjacent frames. The fix is sizing hints, but first you have to *recognize* the runtime frame for what it is.
- **Slice growth.** `append` past capacity calls `runtime.growslice`, which allocates a larger backing array (and copies). A loop that `append`s without preallocating shows up as `growslice` churn, not as your code.
- **Channel buffers, goroutine stacks, defer records.** Buffered channels allocate their ring buffer; growing a goroutine's stack allocates; `defer` in older Go allocated a `_defer` record (mostly stack-allocated in modern Go, but not always). These appear as runtime frames.

Seeing `runtime.growslice` or `runtime.mapassign` high in the profile is a *signal to preallocate*, not a bug in the runtime.

**`[]byte`↔`string` conversions allocate by default.** `string(b)` for a `[]byte` and `[]byte(s)` for a string both **copy** — because Go strings are immutable and slices are not, the conversion must allocate a fresh backing array to preserve that invariant. In hot parsing/serialization paths these conversions are a top allocation source and are easy to miss because they look like free syntax. (The compiler optimizes a *few* special cases — e.g. `string(b)` used only as a transient map key in `m[string(b)]`, or ranging `for _, r := range string(b)` — to avoid the copy, but the general conversion allocates.)

**Reflection and JSON are allocation storms.** `encoding/json` (and reflection generally) allocates prolifically: per-field boxing into `interface{}`, intermediate maps for `map[string]interface{}` decoding, reflect `Value` churn, and growing buffers. An endpoint that marshals/unmarshals JSON in its hot path will frequently have `encoding/json` and `reflect` dominating its `alloc_space` — which is *expected*, and the lever is a codegen serializer or `jsoniter`-style approach, not a micro-fix. Recognize the signature so you don't try to optimize your own code when 80% of the churn is in the JSON reflection path.

> **Key insight:** Three classes of allocation aren't where they look: **inlined** allocations are credited to the call site, **runtime-internal** allocations (`growslice`/`mapassign`/channel buffers) come from your *failure to pre-size* rather than from explicit `new`, and **`[]byte`↔`string` plus reflection/JSON** allocate behind innocent-looking syntax. Reading these correctly is most of what separates a senior from someone chasing a flame graph in circles.

---

## Continuous Allocation Profiling in Production

The allocation pattern that matters is the one under *real* traffic, not your benchmark. Continuous profiling — capturing low-overhead allocation profiles from production continuously and storing them over time — is how seniors catch allocation regressions that never show up in a microbenchmark.

The mechanism is the same Poisson/TLAB sampler running with a *production-safe* rate. Go already samples heap allocations by default (`MemProfileRate = 512 KiB`) with overhead low enough to leave on in production — the heap profile is always available at `/debug/pprof/heap` (or `pprof.Lookup("allocs")`). A continuous-profiling agent (Grafana Pyroscope, Polar Signals/Parca, Datadog, Google Cloud Profiler) scrapes that endpoint on an interval, tags each profile with version/instance/commit, and stores it so you can query "allocation by call site, over time, across the fleet."

```go
import "net/http"
import _ "net/http/pprof"   // registers /debug/pprof/{heap,allocs,...}

func main() {
    go func() { http.ListenAndServe("localhost:6060", nil) }()
    // ... your service ...
}
```

```bash
# Pull a live allocation (churn) profile from a running service:
go tool pprof http://localhost:6060/debug/pprof/allocs        # alloc_space/objects (cumulative)
go tool pprof http://localhost:6060/debug/pprof/heap          # same data; default view is inuse
```

What continuous allocation profiling unlocks that one-off profiling can't:

- **Regression attribution by deploy.** When GC CPU jumps after a release, you diff the allocation profile *across the version boundary* (exactly the `-base` diff from earlier, but automated across deploys) and the new call site is right there. This is the production analog of the differential profile.
- **Tail-correlated profiling.** A profile averaged over a minute hides the allocation spike that caused a 2-second pause. Production profilers that can slice the profile to a *time window* (or correlate with a trace) let you ask "what was allocating during the p99 latency event?"
- **Fleet-wide aggregation.** One instance's profile is noisy (it's a sampler); aggregating across hundreds of instances tightens the estimate and surfaces call sites no single instance would show clearly.

On the JVM, the equivalent is **continuous JFR** (always-on flight recording with `settings=profile` and disk-based circular buffers) or async-profiler in a continuous-profiling agent, capturing `jdk.ObjectAllocationSample` continuously at bounded overhead. The JFR design — rate-limited events, on by default in many production setups — exists precisely so allocation sampling can run in production indefinitely.

The senior's posture: **allocation profiling is not a thing you turn on during an incident — it's a thing that's always recording, so that when GC CPU or tail latency moves, the allocation delta that caused it is already captured.**

> **Key insight:** Go's default heap sampler is cheap enough to leave on in production, and a continuous-profiling agent turns "scrape `/debug/pprof/allocs` on an interval, tagged by version" into deploy-attributed, time-windowed, fleet-aggregated allocation data — so an allocation regression is diffed against the previous release automatically instead of reproduced by hand after the fact.

---

## Common Mistakes

1. **Reading `alloc_space` when the problem is object count (or vice versa).** A million 64-byte allocations are invisible in `-alloc_space` next to one 8 MiB buffer, but they may be what's hammering the GC. Always open both views.

2. **Treating a two-sample call site as an exact number.** pprof prints the unsampled estimate to the byte even when it rests on two samples. Per-call-site precision requires more samples — lower `MemProfileRate` for a targeted run if you need it.

3. **Confusing `alloc_*` (churn) with `inuse_*` (retention).** Optimizing allocation rate won't fix a leak, and chasing retained objects won't lower GC frequency. Churn is this page; retention is [Memory Profiling](../02-memory-profiling/senior.md). They're different columns of the same profile for a reason.

4. **Comparing before/after profiles taken at different sample rates or loads.** Two estimators with different noise floors aren't a clean diff. Pin `MemProfileRate` and the workload, use `-base`, and confirm with an exact `-benchmem` assertion.

5. **Blaming the runtime for `runtime.growslice` / `runtime.mapassign`.** Those frames are the symptom of *your* un-pre-sized slice or map rehashing as it grows. The fix is a capacity hint (`make([]T, 0, n)`, `make(map[K]V, n)`), not avoiding the data structure.

6. **Forgetting that `[]byte`↔`string` copies.** `string(b)` and `[]byte(s)` allocate a fresh backing array every time (immutability invariant). In hot parse/serialize paths they're a top source; they just don't *look* like allocations.

7. **Setting `MemProfileRate` after allocations have already happened.** The runtime arms the sampler with the value it sees first. Set it in `init()` or at the top of `main`, not deep in request handling, or your profile under-samples everything before the change.

8. **Optimizing your own code when JSON/reflection is 80% of the churn.** If `encoding/json` and `reflect` dominate the profile, the lever is a codegen serializer, not micro-tuning your handlers. Read whose frames they are first.

---

## Apply it

1. State the system invariant that **Allocation Profiling** must protect.
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

- Which invariant must remain true when Allocation Profiling fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
