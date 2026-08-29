# Allocation Profiling — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Allocation Profiling** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Profiling](../README.md) → Allocation Profiling
> *Your garbage collector isn't slow because it's badly written. It's busy because your code keeps handing it garbage to collect. Allocation profiling shows you exactly which lines are doing the handing.*

---

## Core Concept 1 — Allocation Rate vs Live Memory

These two numbers sound similar and are constantly confused. Telling them apart is the foundation of everything below.

- **Live memory** = how much is *alive right now*. A snapshot. "The heap currently holds 400 MB." This is what a **memory profile** answers, and it's the thing to look at when memory keeps *growing* (a leak) or is simply *too large*.

- **Allocation rate** = how much is *created over time*, regardless of whether it's later thrown away. A flow. "This code allocates 2 GB/sec." This is what an **allocation profile** answers, and it's the thing to look at when the **GC runs a lot** or **CPU is spent in GC**.

Here's why the difference matters so much. Consider a function that, on every request, builds a 1 KB temporary buffer, uses it, and discards it:

```
10,000 requests/sec × 1 KB temporary buffer each
  → live memory at any instant: ~1 KB (one buffer in flight)
  → allocation rate:            ~10 MB/sec of pure garbage
```

A memory profile of this code looks *clean* — almost nothing is alive, because each buffer dies immediately. But the program is generating 10 MB of garbage every second, and the GC must run over and over to sweep it up. **Low live memory, high allocation rate.** If you only ever look at a memory profile, this problem is invisible. You need the allocation profile to see it.

> **Key insight:** "Memory is fine, we're only using 1 KB" and "the GC is killing us" are *not contradictory* — they're the classic signature of a high allocation rate. The bytes don't *accumulate*; they *churn*. The cost isn't storage, it's the constant create-and-collect cycle.

The practical rule of thumb: **if memory keeps growing, profile memory (retention). If memory is flat but the GC/CPU is busy, profile allocations (rate).** This page is the second case.

---

## Core Concept 2 — Your First Allocation Profile: `-benchmem`

You don't need a fancy tool to get your first allocation numbers in Go. A benchmark with one flag will do it. This is the single most useful habit you can build at this level.

Suppose you suspect this string-building function allocates too much:

```go
func joinWords(words []string) string {
    s := ""
    for _, w := range words {
        s += w + " "   // each += builds a brand-new string
    }
    return s
}
```

Write a benchmark for it (file `bench_test.go`):

```go
func BenchmarkJoinWords(b *testing.B) {
    words := []string{"the", "quick", "brown", "fox", "jumps"}
    for i := 0; i < b.N; i++ {
        _ = joinWords(words)
    }
}
```

Run it with `-benchmem` — the flag that turns on allocation reporting:

```bash
go test -bench=JoinWords -benchmem
```

```
BenchmarkJoinWords-8    3,000,000    412 ns/op    160 B/op    5 allocs/op
```

Read the last two columns — they are the whole point:

- **`160 B/op`** — this function allocates 160 bytes of heap memory *per call*.
- **`5 allocs/op`** — it makes 5 separate heap allocations *per call*.

Five allocations to join five words. That's not a coincidence — each `s += ...` throws away the old string and builds a new, longer one. The number of allocations grows with the input. Now you have a *measured* fact, not a hunch: this function allocates per word.

> **Key insight:** `allocs/op` and `B/op` are your scoreboard. Before you "optimize" anything, get the number. After you change the code, get it again. If `allocs/op` didn't drop, your change didn't help the allocation problem — no matter how clever it felt. Optimizing without measuring these two numbers is guessing.

A note for other languages so the idea transfers: Java's **JMH** benchmark harness has `-prof gc`, which reports allocation rate per operation in much the same spirit. Python's standard-library **`tracemalloc`** can snapshot allocations and show you the top allocating lines. The tool changes; the question — *how much does this code allocate per unit of work?* — does not.

---

## Core Concept 3 — `alloc_objects` vs `alloc_space`: Many Small vs Few Large

`-benchmem` gives you one function's totals. To see allocations across a *whole program* and attribute them to call sites, you use **pprof** — and pprof asks you which of two questions you want answered.

Generate an allocation profile from a benchmark:

```bash
go test -bench=. -memprofile=mem.out
go tool pprof mem.out
```

Inside pprof, the same data has two lenses:

```
(pprof) sample_index = alloc_objects   # count: HOW MANY allocations
(pprof) sample_index = alloc_space     # bytes: HOW BIG the allocations are
```

These answer genuinely different questions, and the gap between them is diagnostic:

- **`alloc_objects`** counts allocations. A call site high here is allocating **many small things** — think a tight loop creating one tiny object per iteration. Each object is cheap, but there are millions of them, and *the GC's cost is driven by the number of objects*, not their size. This is the view that most often explains GC pressure.

- **`alloc_space`** sums bytes. A call site high here is allocating **a lot of memory**, possibly in **a few large chunks** — think one `make([]byte, 10_000_000)`. One allocation, huge size.

A call site can be a giant in one view and invisible in the other:

```
alloc_objects (count):                 alloc_space (bytes):
  4,000,000  parseRow      ← huge        12 MB   parseRow
        1    loadFile               →   500 MB   loadFile      ← huge
```

`parseRow` made four million tiny allocations (a GC nightmare); `loadFile` made *one* allocation of half a gigabyte (a memory-size concern, but trivial GC work — one object). If GC *pauses* are your problem, you chase `parseRow`. If total *memory* is your problem, you look at `loadFile`. Pick the lens that matches your symptom.

> **Key insight:** "Many small" and "few large" are different diseases with different cures, and a single number can't tell them apart. Always check **both** `alloc_objects` and `alloc_space`. The contrast between them — which call sites jump to the top when you switch lenses — *is* the diagnosis.

---

## Core Concept 4 — Reading Per-Call-Site Counts to Find the Worst Offender

The reason this whole discipline is tractable for a junior: allocations are wildly **unevenly distributed**. You will almost never find allocation spread evenly across your code. Instead, a tiny number of call sites — often *one* — produce the overwhelming majority. Find that one line, fix that one line, and the graph moves. This is the 80/20 rule in its purest form.

pprof's `top` command sorts call sites by the metric you chose, worst first:

```bash
(pprof) sample_index = alloc_objects
(pprof) top
```

```
      flat  flat%   sum%        cum   cum%
  3850000  77.0%  77.0%    3850000  77.0%  main.parseRow
   480000   9.6%  86.6%     480000   9.6%  main.(*Buffer).grow
   210000   4.2%  90.8%     210000   4.2%  encoding/json.Marshal
    95000   1.9%  92.7%      95000   1.9%  main.newSession
```

How to read this without drowning in columns:

- **`flat`** — allocations made *directly in this function's own code*. This is the number you want for finding the offender: it's allocations the function itself is responsible for, not ones made by functions it calls.
- **`flat%`** — that as a percentage of all allocations. `parseRow` is **77%** of every allocation in the program. That's your offender. Everything else is rounding error by comparison.
- **`cum` / `cum%`** — *cumulative*: this function **plus everything it calls**. Useful when the real cost hides in a callee, but start with `flat`.

To see the exact lines inside the worst function, use `list`:

```bash
(pprof) list parseRow
```

```
         .          .   12:  func parseRow(line string) Row {
   1920000          .   13:      parts := strings.Split(line, ",")    ← allocates a slice every call
   1920000          .   14:      tags := make([]string, 0)            ← starts empty, grows repeatedly
         .          .   15:      ...
```

Now you're looking at the precise lines doing the damage — `strings.Split` and an un-presized slice — with allocation counts beside them. This is the payoff of the whole exercise: not "the program allocates a lot," but "**line 13 of `parseRow` allocates 1.9 million times.**" That's a fact you can act on.

> **Key insight:** Don't try to reduce allocations everywhere — that's exhausting and pointless. Find the **top one or two call sites** (by `flat`), confirm the exact lines with `list`, and fix only those. Allocation is so skewed that fixing the #1 offender usually moves the whole program's GC cost more than fixing the next twenty combined.

---

## Core Concept 5 — The Four Junior Culprits

Once you can read a profile, the same handful of patterns will show up at the top again and again. Learn to recognise these four on sight; they cover the large majority of what a junior will find.

**1. String concatenation in a loop.** Strings are immutable in Go (and Java, and Python). `s += x` can't extend the existing string — it must allocate a *whole new one* and copy. In a loop, that's an allocation every iteration, and the strings get longer each time.

```go
s := ""
for _, x := range items {
    s += x          // a new string allocated EVERY iteration
}
```

This lights up `alloc_objects` *and* `alloc_space`. In the profile you'll see the concatenation line with a count proportional to your loop length. (Java's `String +` in a loop is the identical trap; the fix uses a `StringBuilder`.)

**2. Growing a slice without preallocating.** Appending to a slice that starts empty forces the runtime to allocate a bigger backing array and copy everything over each time it runs out of room — repeatedly, as the slice grows.

```go
var out []int                  // capacity 0
for _, v := range src {
    out = append(out, v*2)     // re-allocates the backing array several times as it grows
}
```

In the profile this appears as allocations inside `growslice` (Go's internal grow routine), traced back to your `append` line. The tell is multiple allocations for a slice whose final size you could have known up front.

**3. Boxing a value into an interface.** Putting a concrete value into an `interface{}` (now `any`) — very commonly by passing it to something like `fmt.Sprintf` or storing it in a `map[string]any` — frequently forces the value onto the heap so the interface can hold a pointer to it.

```go
func log(v any) { ... }
for i := 0; i < n; i++ {
    log(i)        // the int 'i' gets boxed onto the heap to fit in 'any'
}
```

This is sneaky because there's no `make` or `new` in sight — the allocation is *implicit*. In the profile you'll see it attributed to the call line, and the `list` view will show an allocation on a line that looks allocation-free. (This is exactly what Java does when it auto-boxes an `int` into an `Integer`, and what Python does because *everything* is already a heap object.)

**4. Defensive copies.** Code that copies a slice or struct "to be safe" — so a caller can't mutate the original — allocates a new buffer every time it runs. Sometimes necessary; often done reflexively on a hot path where it isn't.

```go
func process(data []byte) {
    local := make([]byte, len(data))   // a fresh copy on every call
    copy(local, data)
    ...
}
```

In the profile this is a clean `make` on a hot path, high in both `alloc_objects` and `alloc_space`. The question to ask is never "is the copy correct?" — it's "does *this* path actually need it, given how often it runs?"

> **Key insight:** Three of these four allocations are *invisible in the source* — there's no `make` or `new` on the boxing or concatenation lines. That's precisely why you profile instead of reading code: the profiler sees the heap allocations the syntax hides. Your eyes can't reliably spot an allocation; pprof can't miss one.

---

## Real-World Examples

**1. The "GC is killing us" service that had no leak.** A JSON API shows GC eating 30% of CPU under load. The team's first move is to tune GC settings — no improvement. Someone finally runs `go test -bench=. -memprofile`, switches pprof to `alloc_objects`, and runs `top`. One line — a per-request log call that did `fmt.Sprintf("%v", bigStruct)` — accounts for 60% of all allocations, because formatting boxed every field. Memory usage had always looked *fine* (nothing was retained); the problem was pure churn. Removing one `Sprintf` from the hot path cut GC CPU by more than half. No GC flag was ever touched.

**2. The slice that reallocated eight times.** A data pipeline reads a CSV and builds a slice of rows. `-benchmem` reports `9 allocs/op` for a function that conceptually does *one* thing. `list` reveals the cause: `var rows []Row` starts at capacity zero and `append` grows the backing array repeatedly as the file is read. The final size was knowable from the line count all along. The fix (presizing) is a *Memory Optimization* concern — but it was the **allocation profile** that turned a vague "this feels slow" into "this line reallocates eight times per call."

**3. The "few large" surprise that wasn't a GC problem at all.** An image service occasionally spikes to 2 GB of memory. The team assumes high allocation rate and goes hunting for churn in `alloc_objects` — and finds nothing remarkable. Switching to `alloc_space` tells the real story: a single `make([]byte, ...)` that decodes a full-resolution image. *One* allocation, but enormous. This is a "few large" case: it's a memory-*size* issue (relevant to a memory profile and to capacity planning), not a GC-pressure issue. The lesson: checking *both* lenses stopped them from chasing the wrong problem.

---

## Common Mistakes

1. **Blaming the GC instead of the allocation rate.** "The GC is slow" is almost never the real issue. The GC runs proportionally to how much you allocate. Profile allocations *first*; tune the GC approximately never. Reaching for `GOGC` before opening an allocation profile is treating the symptom.

2. **Looking only at live memory when the symptom is GC/CPU.** A memory profile of a high-churn program looks *clean* — everything dies immediately, so nothing is retained. If your symptom is "GC is busy" or "CPU is high in GC," the memory profile will mislead you into thinking there's no problem. Use the allocation profile.

3. **Checking only one of `alloc_objects` / `alloc_space`.** "Many small" and "few large" are different problems. A call site can dominate one view and vanish in the other. Always look at both; the contrast is the diagnosis.

4. **Optimizing call sites that aren't at the top.** Allocation is heavily skewed — one or two call sites usually dominate. Shaving allocations off a function that's 0.5% of the total is wasted effort. Sort by `flat`, fix the top, re-measure.

5. **"Optimizing" without re-measuring `allocs/op`.** You changed the code and it *feels* leaner. Did `allocs/op` actually drop? If you didn't re-run `-benchmem`, you don't know — and "felt faster" has sent many engineers down the wrong path. The number is the only verdict.

6. **Confusing "where it's allocated" with "where it's retained."** An allocation profile tells you the line that *created* the memory. It does **not** tell you what's keeping memory *alive* — that's a memory (retention) profile, a different tool answering a different question. Don't use an allocation profile to hunt a leak.

---

## Apply it

1. Choose one small, known input for **Allocation Profiling**.
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

- What problem does Allocation Profiling solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
