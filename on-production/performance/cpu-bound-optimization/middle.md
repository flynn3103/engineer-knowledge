# CPU-Bound Optimization — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **CPU-Bound Optimization** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Performance](../README.md) → CPU-Bound Optimization
> *The junior page taught you to suspect the CPU and to profile before touching anything. This page is what you do once the profile points the finger: how to read it, why a cache miss costs 100 arithmetic ops, and the concrete moves — data layout, fewer allocations, inlining, bounds-check elimination, predictable branches — that turn a hot loop from slow to fast.*

---

## Reading a CPU Profile — Flat vs Cumulative

A CPU profile is a histogram of where the program was when the profiler sampled the stack — typically ~100 times per second per core. Every profiler exposes two numbers per function, and confusing them sends you optimising the wrong code.

- **Flat (self) time** — samples landed *directly inside this function's own instructions*, not in something it called. This is the work the function itself does.
- **Cumulative (total) time** — samples landed in this function *or anything it called, transitively*. This is the cost of the whole subtree rooted here.

```
(pprof) top -cum
  flat  flat%   cum   cum%
 0.05s   1.2%  3.80s  89%   main.processBatch     ← huge cum, tiny flat: just a caller
 2.90s  68.0%  2.90s  68%   main.scoreRecord      ← huge flat: THIS is the hot code
 0.40s   9.4%  0.55s  13%   runtime.mapaccess2    ← map lookups, real self cost
```

- `processBatch` has 89% cumulative but 1.2% flat — it's a dispatcher; optimising its body buys nothing.
- `scoreRecord` has 68% *flat* — the actual work lives there.
- **Optimise on flat time; navigate with cumulative time.** Cumulative tells you which call path to descend; flat tells you where to stop and start editing.

Two refinements make this sharper:

1. Use the flame graph (`go tool pprof -http=:8080`) to *see* the call tree — width is cumulative time, and a wide plateau with no children on top of it is pure self time, your prime target.
2. Watch for `runtime.*` frames bubbling up: a big `runtime.mallocgc` or `runtime.gcBgMarkWorker` means your "CPU" problem is really an *allocation* problem in disguise (see [05 — Memory & Allocation Profiling](../memory-and-allocation-profiling/middle.md)).

> **Key insight:** Flat time is *where the cycles burn*; cumulative time is *the route to get there*. A function can dominate the profile (high cumulative) and contain nothing worth fixing (low flat). Always confirm a function's *own* code is hot before you touch it — otherwise you're polishing a hallway.

---

## The Memory Hierarchy — Why Cache Misses Dominate

The single fact that reframes most CPU optimisation: **the CPU is not waiting on arithmetic — it's waiting on memory.** A modern core executes several integer operations *per nanosecond*, but fetching a value that isn't in cache can stall it for ~100 nanoseconds. The arithmetic was never the bottleneck; the *data movement* was.

Rough latencies, in CPU cycles (≈0.3 ns each on a 3 GHz core):

| Where the data is | Latency (cycles) | Latency (ns) | Relative |
|---|---|---|---|
| Register | ~0 | — | 1× |
| L1 cache | ~4 | ~1.3 | ~4× |
| L2 cache | ~12 | ~4 | ~12× |
| L3 cache | ~40 | ~13 | ~40× |
| Main memory (RAM) | ~200 | ~65 | ~**200×** |

- An L1 hit and an `add` are roughly the same cost.
- A trip to RAM is **~100× a single arithmetic operation.**
- This is why "reduce the number of operations" is often the *wrong* optimisation and "reduce the number of cache misses" is the right one.

**Two hardware behaviours you can exploit:**

1. **Cache lines.** Memory moves in 64-byte lines, not single bytes. Touch one `int`, and the 7 neighbours on its line come along free. Lay data so the bytes you use next are *on the same line* and you get those accesses essentially for free.
2. **The hardware prefetcher.** The CPU detects *sequential* access patterns and fetches lines ahead of you. Walk an array forward → the prefetcher hides the latency. Chase pointers to random heap addresses → it can't predict, and you eat the full ~200-cycle miss every time.

> **Key insight:** Count cache misses, not operations. A loop doing twice the arithmetic on contiguous, cache-resident data routinely beats a "cleverer" loop that does half the arithmetic but chases pointers across the heap. Memory access *is* the dominant cost; algorithmic op-counting that ignores the memory hierarchy is counting the wrong thing.

---

## Data-Oriented Design — Layout Is Performance

If cache misses dominate, **how you arrange data in memory is a first-class performance decision** — often bigger than any algorithmic tweak. The canonical lever is *array-of-structs* (AoS) vs *struct-of-arrays* (SoA).

Suppose you score a million particles using only their `x` and `y`, but each particle also carries 48 bytes of other state:

```go
// Array of Structs (AoS) — the natural OO layout
type Particle struct {
    x, y    float64   // 16 bytes we use
    vx, vy  float64
    mass    float64
    name    string    // 16 bytes
    tags    []string  // 24 bytes ... ~64 bytes total
}
particles := make([]Particle, 1_000_000)

func sumX(ps []Particle) (s float64) {
    for i := range ps { s += ps[i].x }   // we read x; the cache line drags 48 unused bytes
    return
}
```

- Each `Particle` is ~64 bytes — one whole cache line. To sum `x`, every iteration loads a full line but uses 8 of its 64 bytes. You're paying a memory miss to fetch mostly garbage.

```go
// Struct of Arrays (SoA) — hot fields packed together
type Particles struct {
    x, y   []float64   // x[] is dense: 8 used bytes per 8 bytes loaded
    vx, vy []float64
    mass   []float64
    name   []string
}

func sumX(p *Particles) (s float64) {
    for _, v := range p.x { s += v }   // pure sequential scan over packed float64s
    return
}
```

- Now one cache line holds 8 `x` values, all of which you use, and the prefetcher sees a perfect sequential stream.
- Same arithmetic, ~6–8× fewer cache misses on the hot field.
- A typical measured result: **AoS ~4.1 ms, SoA ~0.6 ms** for the million-element sum — a 6–7× win with zero change to the math.

The deeper principle: **reduce pointer chasing.**

- A `[]*Node` linked list scatters nodes across the heap; traversing it is a sequence of unpredictable misses.
- A `[]Node` slice (or an index-based "linked list" inside one array) keeps nodes contiguous and prefetchable.
- Prefer indices over pointers and contiguous slices over node graphs whenever you traverse hot data.

> **Key insight:** The compiler optimises your *instructions*; only you can optimise your *data layout*. Group the fields you touch together so a 64-byte cache line carries 64 bytes of *useful* data. AoS→SoA is the highest-leverage CPU optimisation that most code never tries.

---

## Killing Allocations in Hot Loops

Every heap allocation in a hot loop costs three ways: the allocation itself, the eventual garbage-collection cost of reclaiming it, and the cache pollution of touching fresh memory. In Go and Java, an allocation-heavy loop often shows up as "CPU time in `runtime.mallocgc`" or "time in GC" — a CPU symptom with an allocation cause.

The fix is **escape analysis awareness** plus **buffer reuse**.

- Go's compiler tries to keep allocations on the stack (free) rather than the heap (GC-managed); a value *escapes* to the heap when its lifetime outlives the function.
- Ask the compiler what it decided:

```bash
go build -gcflags='-m' ./...
# ./score.go:14:13: make([]byte, 256) escapes to heap   ← allocated per call, GC'd later
# ./score.go:22:9:  &buf does not escape                  ← stays on stack, free
```

A classic offender allocates a scratch buffer every iteration:

```go
// BEFORE: allocates a fresh slice every call → 1M heap allocs
func format(rows []Row) []string {
    out := make([]string, 0, len(rows))
    for _, r := range rows {
        buf := make([]byte, 0, 64)          // escapes; heap alloc per row
        buf = strconv.AppendInt(buf, r.ID, 10)
        out = append(out, string(buf))
    }
    return out
}
```

Hoist the buffer out and reuse it; for cross-call reuse, a `sync.Pool` gives each goroutine its own scratch space:

```go
// AFTER: one reusable buffer; allocations drop ~1M → a handful
func format(rows []Row) []string {
    out := make([]string, 0, len(rows))
    buf := make([]byte, 0, 64)              // allocated ONCE
    for _, r := range rows {
        buf = buf[:0]                       // reset length, keep capacity
        buf = strconv.AppendInt(buf, r.ID, 10)
        out = append(out, string(buf))
    }
    return out
}
```

- `buf[:0]` keeps the backing array and resets length — no new allocation.
- Benchmark with `-benchmem` to see it land:

```
BEFORE  1240 ns/op   1056 B/op   17 allocs/op
AFTER    410 ns/op    192 B/op    1 allocs/op
```

- A 3× speedup, none of it from changing the algorithm — purely from not asking the allocator and GC to run on the hot path.
- The same pattern in Java is object pooling or, better, primitive arrays instead of boxed `Integer[]`; in C++ it's reserving `std::vector` capacity and reusing it rather than reallocating per call.

> **Key insight:** Allocation is hidden CPU work. Each `make`/`new` in a hot loop schedules future GC, pollutes cache, and is itself non-trivial. `-gcflags=-m` shows what escapes; reuse buffers (`buf[:0]`, `sync.Pool`, preallocated arrays) to take the allocator off the hot path entirely.

---

## Function-Call Overhead and Inlining

A function call is not free: arguments go into registers or onto the stack, the return address is saved, control jumps, and on return everything unwinds. For a tiny function called millions of times, this prologue/epilogue can rival the body's own work — *and* it blocks other optimisations, because the compiler can't reason across a call boundary it doesn't inline.

**Inlining** is the cure: the compiler copies a small callee's body into the caller, eliminating the call overhead and exposing the merged code to further optimisation (constant folding, dead-code elimination, bounds-check removal across the seam).

- Go inlines automatically based on a function's cost budget; check what it decided:

```bash
go build -gcflags='-m' ./...
# ./geo.go:8:6: can inline dist          ← small enough; will be inlined
# ./geo.go:20:6: cannot inline solve: function too complex: cost 213 exceeds budget 80
```

```go
func dist(ax, ay, bx, by float64) float64 {   // tiny → inlined
    dx, dy := ax-bx, ay-by
    return dx*dx + dy*dy
}
```

- When `dist` is inlined into a hot loop, the call vanishes *and* the compiler can keep `dx, dy` in registers across what used to be a boundary.
- The reverse trap: a function that's *almost* small enough but trips the budget (often by containing a `defer`, a closure, or a `panic`/`recover`) silently stops inlining and gets slow.
- If `-m` says `cannot inline ... too complex`, splitting out the hot path into a separate tiny function can restore inlining.

> **Key insight:** Inlining is worth more than the call overhead it removes — it *unlocks* optimisations across the former boundary. Keep hot leaf functions small and free of `defer`/closures so they stay under the inline budget. Don't manually inline by hand first; check `-gcflags=-m` and only intervene where the compiler refuses.

---

## Bounds-Check Elimination and Strength Reduction

In memory-safe languages, every slice/array index access carries an implicit **bounds check** — a compare-and-branch that traps if the index is out of range. In a tight loop, that's an extra branch per element. The compiler *eliminates* the check when it can prove the index is in range; your job is to write code that makes the proof easy.

```go
// BEFORE: compiler can't easily prove each a[i] is in range
func sum(a []int) (s int) {
    for i := 0; i < len(a); i++ { s += a[i] }   // bounds check per iteration (often)
    return
}

// AFTER: range form, or a single hoisted assertion, lets it drop the checks
func sum(a []int) (s int) {
    for _, v := range a { s += v }              // range over slice: no per-elem check
    return
}
```

- The idiomatic `range` form is the most reliable way to get bounds checks removed in Go.
- When you must index, a single `a = a[:n]` reslice or a `_ = a[n-1]` assertion before the loop can give the compiler the fact it needs to elide every check inside.
- Inspect what's left:

```bash
go build -gcflags='-d=ssa/check_bce/debug=1' ./...
# ./sum.go:3:20: Found IsInBounds   ← a bounds check survives here
```

**Strength reduction** is the sibling technique: replace expensive operations with cheaper equivalent ones, and hoist redundant work out of the loop.

```go
// BEFORE: division per iteration (10–40 cycles each), repeated multiply
for i := 0; i < n; i++ { out[i] = data[i] / 8 ; idx := i * stride }

// AFTER: shift instead of divide; strength-reduce the multiply to an add
shift := 3                                  // 8 == 1<<3
idx := 0
for i := 0; i < n; i++ { out[i] = data[i] >> shift; _ = idx; idx += stride }
```

- Division is one of the slowest integer ops; a power-of-two divide becomes a shift.
- A loop-variable multiply (`i*stride`) becomes a running addition.
- Compilers do much of this automatically, but hoisting *invariant* computation (anything not depending on the loop variable) out of the loop is squarely your job — recomputing `len(s)` or a struct-field lookup every iteration is pure waste.

> **Key insight:** Memory-safe languages tax you with a hidden branch per index; write loops the compiler can prove safe (`range`, single hoisted assertion) and that tax disappears. Then strip redundant work: hoist loop invariants, replace divide-by-constant with shifts, and let strength reduction turn multiplies into adds.

---

## Branch-Heavy Code and Predictability

Modern CPUs are deeply pipelined: they guess which way a branch will go and execute ~15–20 instructions ahead *speculatively*. A correct guess is free. A **misprediction** throws away that speculative work and refills the pipeline — a penalty of ~15–20 cycles, comparable to an L3 cache miss. A branch the predictor can't guess is therefore expensive *even though the comparison itself is one instruction*.

The famous demonstration: summing only the values above a threshold runs dramatically faster when the array is *sorted*, because the branch becomes predictable.

```go
func sumAbove(a []int, t int) (s int) {
    for _, v := range a {
        if v >= t { s += v }   // unsorted: ~50% mispredict; sorted: ~always right
    }
    return
}
// unsorted input: ~3.2 ms   |   same data sorted first: ~0.9 ms  (≈3.5× from prediction alone)
```

**Two ways to help the predictor:**

1. **Make branches predictable** — sort or partition data so the common case dominates, or hoist a condition out of the loop so it's decided once instead of per element.
2. **Make branches disappear (branchless code)** — compute both sides and select arithmetically, so there's no branch to mispredict. This wins *only* when the branch was genuinely unpredictable; for a well-predicted branch, the branchful version is faster because the predictor already made it free.

```go
// branchless max — no misprediction possible, but always does both subtractions
func maxBranchless(a, b int) int {
    d := a - b
    return b + (d & (d >> 63))   // sign trick; profile to confirm it actually wins
}
```

> **Key insight:** A mispredicted branch costs as much as an L3 miss — the comparison is cheap, the *wrong guess* is not. Predictable branches (sorted/partitioned data) are nearly free; only reach for branchless tricks when profiling proves the branch is genuinely 50/50, and always measure, because branchless code does *both* sides every time.

---

## Worked Example — Reading `perf stat` Before and After

`perf stat` gives you the hardware view a flame graph can't: instructions-per-cycle (IPC), cache misses, branch mispredictions. These numbers tell you *which* technique above to reach for. Take the AoS particle sum from earlier and measure it before and after the SoA rewrite.

```bash
# BEFORE — AoS layout: summing one field out of a 64-byte struct
perf stat -e cycles,instructions,cache-references,cache-misses,branch-misses ./sum_aos

#   8,940,231,005   cycles
#   6,210,440,118   instructions          #   0.69  insn per cycle   ← IPC < 1: STALLING
#     412,330,901   cache-references
#     198,774,540   cache-misses          #  48.2% of cache refs     ← memory-bound
#       3,221,114   branch-misses
#         4.12 ms   time elapsed
```

- IPC of **0.69** is the headline: less than one instruction retired per cycle means the core spends most of its time *waiting*, and the 48% cache-miss rate says it's waiting on memory. This is a layout problem, not a "do less arithmetic" problem.

Apply SoA so the hot field is contiguous, then re-measure:

```bash
# AFTER — SoA layout: x[] packed contiguously
perf stat -e cycles,instructions,cache-references,cache-misses,branch-misses ./sum_soa

#   1,310,887,442   cycles
#   5,980,002,771   instructions          #   4.56  insn per cycle   ← IPC > 4: FED
#      54,201,338   cache-references
#       2,910,664   cache-misses          #   5.4% of cache refs     ← prefetcher working
#       3,180,201   branch-misses
#         0.61 ms   time elapsed
```

- Almost the *same instruction count* (~6 billion), but **6.8× faster wall time** — entirely because IPC jumped from 0.69 to 4.56 and cache misses fell from 48% to 5%.
- The CPU was always able to do the work; it was starved for data. **On CPU-bound code, the win usually comes from feeding the CPU, not from reducing its arithmetic.**

**The diagnostic loop:**

- Low IPC + high cache-misses → fix data layout (SoA, contiguity).
- High IPC but high branch-misses → fix branch predictability.
- Lots of time in `mallocgc`/GC frames → fix allocations.
- Read the counters first; they tell you which chapter of this page applies.

---

## Common Mistakes

1. **Optimising on cumulative time.** A function with 90% cumulative and 2% flat is a dispatcher — editing it does nothing. Confirm *flat* time is high before you touch a function.

2. **Counting operations, ignoring memory.** "I halved the arithmetic" can still be slower if it added pointer chasing. A cache miss is ~100 arithmetic ops; optimise misses, not op-counts.

3. **Keeping the OO/AoS layout on hot data.** A struct with 6 fields where the loop reads 1 wastes 80%+ of every cache line. Split hot fields into their own arrays (SoA) before reaching for cleverer math.

4. **Allocating in the loop body.** A `make`/`new` per iteration turns a CPU problem into a GC problem. Hoist and reuse (`buf[:0]`, `sync.Pool`); confirm with `-benchmem` and `-gcflags=-m`.

5. **Hand-inlining instead of asking the compiler.** Inlining is automatic and budget-driven. Don't manually splice functions together — run `-gcflags=-m`, find what *won't* inline, and fix the cause (drop a `defer`, shrink the function).

6. **Reaching for branchless tricks on predictable branches.** Branchless code does both sides every time. It only wins on genuinely unpredictable (≈50/50) branches; on a well-predicted branch it's *slower*. Measure before converting.

7. **Trusting "it's faster" without re-profiling.** Every change shifts the bottleneck. The thing you optimised may no longer be hot; re-run the profiler and `perf stat` after each round.

---

## Apply it

1. Find a real component where **CPU-Bound Optimization** affects an interface or dependency.
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

- Which boundary is most affected by CPU-Bound Optimization?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
- When is a micro-optimization the right move instead of an algorithmic one?
- State Amdahl's law and explain how it decides which hot path to attack.
- A profile shows time spread evenly across 20 functions with no clear hot spot — what does that tell you?
- What's the rough cost, in cycles, of an L1 hit vs an L2 hit vs an LLC hit vs a main-memory access, and why do these numbers dominate optimization?
- Explain AoS vs SoA and when SoA wins.
- Why is pointer chasing (e.g., a linked list) often dramatically slower than iterating an array, even at the same Big-O?
