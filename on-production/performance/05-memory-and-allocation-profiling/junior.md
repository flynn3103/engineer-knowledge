# Memory and Allocation Optimization — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Memory and Allocation Optimization** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Performance](../README.md) → Memory and Allocation Optimization
> *Two programs can use the exact same amount of memory at any instant — and one of them can be three times slower. The difference is not how much memory you hold, but how often you ask for it.*

---

## Core Concept 1 — Two Different Numbers: Residency vs Allocation Rate

These two numbers get conflated constantly, and untangling them is the single most useful thing on this page.

**Residency** (a.k.a. heap size, live set) is a *snapshot*: how much memory is alive right now. Think of it as the water level in a tank.

**Allocation rate** is a *flow*: how fast new memory is being requested over time. Think of it as the rate water pours in — *and* drains out.

A tank can sit at a perfectly stable, low level while a firehose pours in and an equal-sized drain pours out. The level (residency) is small and constant. The *flow* (allocation rate) is enormous. That is the situation that quietly kills performance, because the drain — the garbage collector — is working flat out the whole time.

```
RESIDENCY (snapshot)          ALLOCATION RATE (flow)
"how much is held now"        "how fast new memory is requested"
predicts: OOM / cost          predicts: GC work / speed
measured in: MB held          measured in: MB/s, allocs/op
```

Here's a concrete example of low residency, high allocation rate:

```go
// Processes a million records. At any instant, only ONE record's
// temporary buffer is alive — residency is tiny.
for _, rec := range records {        // a million iterations
    buf := make([]byte, 4096)        // allocate 4 KB... every... iteration
    n := format(buf, rec)
    sink(buf[:n])
}                                    // buf becomes garbage immediately
```

At no point does this hold more than a few kilobytes (low residency). But it allocates **4 GB total** across the loop (a million × 4 KB) — all of it garbage the GC must chase. The fix isn't "use less memory at once"; it's "stop *churning*": allocate the buffer once, outside the loop, and reuse it.

> **Key insight:** A flat memory graph does **not** mean your program is memory-efficient. It can mean you're allocating and discarding at exactly the rate the GC reclaims — a treadmill that looks calm but burns CPU continuously. Always look at *allocation rate*, not just the heap-size line.

---

## Core Concept 2 — Stack vs Heap: Where Does It Live?

Not all memory is equal. There are two places your data can live, and the difference is the difference between *free* and *not free*.

**The stack** is per-function scratch space. When a function is called, it gets a frame; when it returns, the frame vanishes and everything in it is gone — instantly, automatically, at zero cost. No GC is ever involved. Stack memory is the fastest memory there is.

**The heap** is for things that must outlive the function that created them — a value you return a pointer to, something you store in a long-lived map, anything whose lifetime the compiler can't predict. Heap memory is managed by the GC, and *every* heap allocation is work: now, to allocate it, and later, to collect it.

The compiler decides which place each value goes, using **escape analysis**: "does this value *escape* the function?" If it can prove the value never outlives the function, it stays on the stack (free). If the value escapes — leaks out via a returned pointer, a closure, an interface — it must go on the heap.

```go
// Stays on the STACK — never escapes. Effectively free.
func sum(xs []int) int {
    total := 0          // local int, dies with the function
    for _, x := range xs {
        total += x
    }
    return total
}

// ESCAPES to the heap — we return a pointer to a local.
func makePoint(x, y int) *Point {
    p := Point{x, y}    // p must outlive this function...
    return &p           // ...so it escapes → heap allocation
}
```

In Go you can ask the compiler to *show* you its decisions:

```bash
go build -gcflags='-m' .
# ./main.go:14:9: &p escapes to heap
# ./main.go:6:13:  xs does not escape
```

That `escapes to heap` line is the compiler telling you exactly where an allocation will happen. Java and Python don't expose this as cleanly — in Python, essentially *everything* is a heap object — but the principle is universal: values that escape their creating scope cost more.

> **Key insight:** Stack allocation is free; heap allocation is not. The best optimization isn't allocating cleverly — it's *not allocating at all* by keeping values from escaping. "Allocates zero times" beats "allocates efficiently" every time.

---

## Core Concept 3 — What the Garbage Collector Actually Does

To understand why allocating less makes code faster, you need a one-paragraph model of the GC — not the algorithm (that's [Language Internals](../../../language-internals/)), just the *cost*.

The collector's job: periodically scan the heap, find every object that's still reachable (still in use), and reclaim everything else so the memory can be handed out again. To do this safely it needs to know nothing is changing underneath it, so it competes with — and sometimes briefly **pauses** — your actual program. The more you allocate, the sooner the heap fills the trigger threshold, the more often the collector runs, the more total CPU it spends, and the more your program stalls.

```
allocate more  →  GC triggers sooner  →  GC runs more often
              →  more CPU spent collecting  →  less CPU left for YOUR work
              →  more (and sometimes longer) pauses  →  worse latency
```

Concretely, Go's GC aims to keep its overhead modest, but a churn-heavy service can easily spend **20–30% of its CPU** just collecting garbage. That's a third of your machine doing nothing but cleaning up after allocations you didn't need to make. Cut the allocation rate in half and you can hand that CPU back to the work that matters — often a *bigger* win than any algorithmic micro-tweak.

The causal chain is the whole point: **you don't optimize the GC, you optimize the input to the GC.** You can't make collection cheaper, but you can give it less to collect. Less garbage in → less GC out.

> **Key insight:** The GC is a tax on allocation. You can't lower the tax *rate*, but you control the *taxable amount*. Every allocation you avoid is GC work that never happens — that's why "allocate less" is the most reliable performance lever a junior has.

---

## Core Concept 4 — The Junior Wins: Allocate Less

Most allocation waste comes from a handful of patterns. Learn to spot these and you'll fix the majority of real-world churn without any cleverness.

**1. Don't allocate inside hot loops.** Hoist the allocation out and reuse it.

```go
// BAD: allocates a fresh buffer every iteration
for _, rec := range records {
    buf := make([]byte, 0, 256)
    buf = append(buf, rec.Bytes()...)
    write(buf)
}

// GOOD: one buffer, reused; reset length, keep capacity
buf := make([]byte, 0, 256)
for _, rec := range records {
    buf = buf[:0]                     // reset length, keep the backing array
    buf = append(buf, rec.Bytes()...)
    write(buf)
}
```

**2. Preallocate slices and maps with capacity.** A slice that grows by `append` reallocates and copies repeatedly (typically doubling) as it expands. If you know roughly how big it'll get, say so up front.

```go
// BAD: grows from nothing — ~log2(n) reallocations and copies
out := []int{}
for _, x := range src { out = append(out, x*2) }

// GOOD: one allocation, no copies
out := make([]int, 0, len(src))       // capacity hint
for _, x := range src { out = append(out, x*2) }

// Same idea for maps:
m := make(map[string]int, len(src))   // avoids repeated rehashing/growth
```

**3. Build strings without concatenation in loops.** In most languages strings are immutable, so `s = s + x` allocates a *brand-new* string every iteration — O(n²) allocation for n pieces.

```go
// BAD: a new string allocated each loop — quadratic churn
s := ""
for _, p := range parts { s += p }

// GOOD: one growing buffer, then one final string
var b strings.Builder
b.Grow(estimatedSize)                 // optional capacity hint
for _, p := range parts { b.WriteString(p) }
s := b.String()
```

The same trap exists everywhere: in Java use `StringBuilder`, not `+=` in a loop; in Python use `"".join(parts)`, not `s += p`.

**4. Avoid unnecessary copies.** Passing a large struct *by value* copies it; passing a slice already shares its backing array (cheap), but `append`-ing to a shared slice can quietly allocate. Pass big things by pointer/reference when you don't need a copy.

> **Key insight:** None of these are clever. They're the same move four times: *move the allocation out of the repeated path, or size it correctly so it happens once.* "Once, ahead of time" beats "every iteration." Master this one habit and you've captured most of the available memory wins.

---

## Core Concept 5 — How to SEE Allocations

You can't optimize what you can't measure, and you should *never* guess. Go makes the measurement almost trivial with benchmarks.

Write a benchmark, run it with `-benchmem`, and read `allocs/op`:

```go
func BenchmarkJoin(b *testing.B) {
    parts := []string{"a", "b", "c", "d", "e"}
    b.ReportAllocs()
    for i := 0; i < b.N; i++ {
        _ = strings.Join(parts, "")
    }
}
```

```bash
go test -bench=Join -benchmem
# BenchmarkJoin-8   12000000   95 ns/op   16 B/op   1 allocs/op
```

Read the last three columns:

- **`ns/op`** — time per operation (the speed).
- **`B/op`** — bytes allocated on the heap per operation.
- **`allocs/op`** — *number of heap allocations* per operation. **This is your primary target.**

Now compare the bad string-concat version against the `strings.Builder` version:

```bash
# Naive  s += p in a loop:
BenchmarkConcat-8    900000   1320 ns/op   248 B/op   7 allocs/op
# strings.Builder:
BenchmarkBuilder-8  4200000    280 ns/op    64 B/op   2 allocs/op
```

The numbers tell the whole story: 7 allocs/op → 2 allocs/op, and the time dropped ~4.7×. You didn't *guess* it was faster — you measured fewer allocations and confirmed the speedup. That's the loop: change code, rerun `-benchmem`, watch `allocs/op` fall.

For *where in a running program* the allocations come from — heap profiles, flame graphs, the actual `pprof` mechanics — see [01 — Profiling](../01-profiling/01-cpu-profiling/junior.md). That topic owns the "how to capture" question; this one owns "what the numbers mean and how to bring them down." The junior rhythm is: benchmark first to quantify, profile only when you need to *locate*.

> **Key insight:** `allocs/op` is the number to drive toward zero. It's deterministic, it's cheap to measure, and "this benchmark went from 7 allocs/op to 1" is a concrete, reviewable, regression-checkable win — far more reliable than eyeballing a timing number that wobbles run to run.

---

## Real-World Examples

**1. The log line that doubled GC load.** A service logs one structured line per request via `fmt.Sprintf("%s %d %v", ...)` plus a few string concatenations — about 12 allocations per request. At 5,000 requests/second that's 60,000 allocations/second of pure churn, and GC overhead sat near 28% of CPU. Switching to a zero-allocation logger that writes directly into a reused buffer dropped it to ~1 alloc/request; GC overhead fell to under 8%, and p99 latency improved because of fewer pauses. The *residency* barely moved — the win was entirely in allocation *rate*.

**2. The slice that grew the hard way.** A data-import job built a result slice with `append` starting from `nil`, for ~2 million rows. Because the slice doubled its backing array as it grew, it reallocated and copied roughly 21 times, touching gigabytes of throwaway memory. One line — `make([]Row, 0, expectedRows)` — removed every one of those reallocations. Import time dropped 35% with no algorithm change at all.

**3. The "small heap, slow service" puzzle.** A team chased a latency problem assuming a memory leak, because the service "felt heavy." But the heap graph was flat and low — no leak. The real culprit was allocation rate: a hot JSON-parsing path allocated a fresh map per message. A heap *profile* (captured per [01 — Profiling](../01-profiling/01-cpu-profiling/junior.md)) pointed at the exact line; reusing a pooled map collapsed the allocation rate and the latency followed. Lesson: low residency hid a high-churn problem in plain sight.

---

## Common Mistakes

1. **Watching heap size and ignoring allocation rate.** A flat memory graph feels safe, but it can hide a treadmill of allocate-and-discard that pins the GC at 25% CPU. The flat line is the *level*; you also need the *flow*.

2. **Allocating inside the hot loop.** `buf := make(...)` *inside* a million-iteration loop is the single most common churn source. Hoist it out and `buf = buf[:0]` to reset — same capacity, zero new allocations.

3. **Growing slices/maps from empty when the size is known.** Starting from `nil`/`{}` forces repeated reallocation and copying. If you can estimate the final size, pass it as a capacity hint and pay for one allocation instead of log(n).

4. **String concatenation in a loop.** `s += x` allocates a whole new string every iteration — quadratic churn. Use `strings.Builder` (Go), `StringBuilder` (Java), or `"".join(...)` (Python).

5. **Guessing instead of measuring.** "This feels faster" is not evidence. Run `go test -bench -benchmem` and compare `allocs/op` before and after. Optimize against the number, not the vibe.

6. **Confusing a leak with high churn.** A *leak* is residency that climbs and never falls (you hold references you shouldn't). High *churn* is a flat-but-busy heap. They look different on a graph and have completely different fixes — don't go hunting for a leak when the problem is allocation rate.

7. **Optimizing allocations that don't matter.** Allocation cost matters in *hot paths*. Removing one allocation from code that runs twice at startup is wasted effort. Measure to find the hot path first.

---

## Apply it

1. Choose one small, known input for **Memory and Allocation Optimization**.
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

- What problem does Memory and Allocation Optimization solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
