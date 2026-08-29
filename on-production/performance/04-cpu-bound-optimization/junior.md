# CPU-Bound Optimization — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **CPU-Bound Optimization** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Performance](../README.md) → CPU-Bound Optimization
> *Slow code feels the same whether the CPU is melting or sitting idle waiting on a disk — but the fix is completely different. The first skill in performance work isn't making code fast; it's knowing which kind of slow you have, and then refusing to guess about the rest.*

---

## Core Concept 1 — CPU-Bound vs I/O-Bound

Before you optimize anything, answer one question: **is the CPU busy, or is it waiting?** Everything downstream depends on the answer, and the two cases need opposite fixes.

**CPU-bound** means the processor is the limiting resource. The program is actively computing — looping, sorting, hashing, parsing, doing math — and it would go faster on a faster CPU. The telltale sign: **one CPU core pinned at 100%** for the whole duration of the slow operation.

**I/O-bound** means the program is *waiting* on something external — reading a file, querying a database, calling an API. The CPU is mostly idle during the wait. A faster CPU wouldn't help at all; the program is blocked on disk or network. The telltale sign: the operation takes seconds but CPU usage stays **low** (5%, 10%) the whole time.

How to tell, practically:

```
Open a system monitor (top / Activity Monitor / Task Manager) and run the slow operation.

  One core at ~100% the whole time   → CPU-BOUND   (this page)
  CPU near idle, but it's still slow  → I/O-BOUND   (a different problem entirely)
```

A concrete check on the command line:

```bash
# Run your program under `time` and watch the breakdown:
time ./myprogram

# real    0m8.0s   ← wall-clock time you actually waited
# user    0m7.6s   ← time the CPU spent running YOUR code
# sys     0m0.2s   ← time in the kernel

# user ≈ real  → CPU was busy the whole time → CPU-BOUND
# user ≪ real  → most of the wait was idle   → I/O-BOUND (waiting on something)
```

In the example above `user` (7.6s) is almost the whole `real` (8.0s) — the CPU was working the entire time. That's CPU-bound, and the rest of this page applies. If instead `real` were 8.0s but `user` were 0.3s, the CPU did almost nothing for 8 seconds: you're waiting on I/O, and no algorithm change will help — you'd look at caching the I/O, parallelizing the waits, or fixing a slow query (see the [Diagnostics](../../../diagnostics/) and database skills instead).

> **Key insight:** A faster algorithm only helps a CPU-bound program. If your code is I/O-bound, you can rewrite the math to be 100× faster and the program will be *exactly* as slow, because the CPU was never the thing you were waiting on. Diagnose the *type* of slow before you spend a minute fixing it.

---

## Core Concept 2 — Profile First, Always

You've confirmed you're CPU-bound. The next temptation is to read the code, spot something that *looks* expensive, and "fix" it. Resist. **Where the time goes is almost never where you think.**

A **profiler** runs your program and reports, function by function, where the CPU actually spent its cycles. It replaces your guess with a measurement. In Go, profiling is built in:

```go
import (
    "os"
    "runtime/pprof"
)

func main() {
    f, _ := os.Create("cpu.prof")
    pprof.StartCPUProfile(f)   // start recording
    defer pprof.StopCPUProfile()

    runTheSlowThing()          // your actual work
}
```

Then inspect the result:

```bash
go tool pprof cpu.prof
(pprof) top        # the functions that ate the most CPU, ranked
(pprof) list slowFunc   # line-by-line time inside one function
```

The `top` output ranks functions by how much CPU time they consumed. The function at the top is your target — and it is *routinely* a surprise. Python's equivalent is just as easy:

```bash
python -m cProfile -s tottime myscript.py
# Prints every function, sorted by total time spent inside it.
```

The output's `tottime` column is "time spent in this function itself." The biggest number is where to start.

The reason this matters so much is the **80/20 rule of performance**: roughly 80% of the time is spent in about 20% of the code — often a single loop. Optimizing anything *outside* that 20% is wasted effort no matter how clever it is. A 10× speedup on code that accounts for 2% of runtime saves you 1.8% overall. A 2× speedup on the code that accounts for 80% saves you 40%. The profiler tells you which code is which.

> **Key insight:** Optimization without profiling is gambling with your own time. The profiler is not a "nice to have" — it is the *first* tool you reach for, before reading a single line with intent to change it. Find the 20% that matters; ignore the 80% that doesn't.

---

## Core Concept 3 — The Algorithm Dominates (Big-O Beats Micro-Tricks)

Once the profiler points at the hot function, the first thing to examine is its **algorithm** — its Big-O — not its individual lines. Why? Because algorithmic improvements scale with your data, and micro-optimizations don't.

Consider checking, for each item in a list, whether it appears in another list:

```go
// SLOW — O(n × m): for every item, scan the whole other list.
func countMatches(items, lookup []string) int {
    count := 0
    for _, x := range items {        // n times
        for _, y := range lookup {   //   × m times each
            if x == y {
                count++
                break
            }
        }
    }
    return count
}
```

With 10,000 items and a 10,000-element lookup, that inner scan runs up to 100,000,000 times. Now the same logic with the right data structure:

```go
// FAST — O(n + m): build a set once, then each check is O(1).
func countMatches(items, lookup []string) int {
    set := make(map[string]struct{}, len(lookup))
    for _, y := range lookup {       // m times, once
        set[y] = struct{}{}
    }
    count := 0
    for _, x := range items {        // n times
        if _, ok := set[x]; ok {     //   each lookup is O(1)
            count++
        }
    }
    return count
}
```

This goes from ~100,000,000 operations to ~20,000 — roughly **5,000× less work**. No micro-trick exists that can rescue the first version; the *shape* of the work was wrong. Compare that to the kind of "optimization" beginners reach for first — caching a length, swapping `i++` for `++i`, inlining a tiny call. Those might shave 5–10% off a single line. The data-structure change shaved off 99.98%.

The lesson generalizes. Reach for the right container before anything else:

| Need | Slow choice | Right choice | Why |
|---|---|---|---|
| "Is X present?" | scan a list — O(n) | map / set — O(1) | hash lookup vs linear scan |
| "Look up by key" | scan a list — O(n) | map — O(1) | direct addressing |
| "Keep things sorted" | re-sort each time — O(n log n) | sorted insert / heap | maintain order incrementally |
| "Count occurrences" | nested loop — O(n²) | map of counts — O(n) | one pass |

> **Key insight:** Big-O wins compound with scale; micro-tricks don't. A better algorithm turns "slow at 10,000, dead at 1,000,000" into "fine at both." Always ask *"what's the Big-O of this hot function?"* before you touch a single line — and an accidental nested loop is the most common O(n²) trap there is.

---

## Core Concept 4 — Reducing Work Beats Doing Work Faster

The deepest principle in CPU optimization is almost philosophical: **the fastest work is the work you never do.** Before making a computation faster, ask whether it needs to happen at all, or that *many* times.

**Hoist work out of loops.** If something inside a loop produces the same answer every iteration, compute it *once* before the loop:

```go
// SLOW — len(data) and the regexp compile run every single iteration.
for i := 0; i < len(data); i++ {
    re := regexp.MustCompile(`\d+`)   // recompiled n times!
    process(data[i], re, len(data))
}

// FAST — compute the invariants once, outside the loop.
re := regexp.MustCompile(`\d+`)       // compiled once
n := len(data)
for i := 0; i < n; i++ {
    process(data[i], re, n)
}
```

Compiling that regular expression is expensive; doing it 10,000 times instead of once is 9,999 wasted compilations.

**Memoize repeated computation.** If you compute the same expensive answer for the same input more than once, cache it:

```python
from functools import lru_cache

@lru_cache(maxsize=None)          # remembers results; same input → instant return
def fib(n):
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)
```

Without the cache, `fib(35)` recomputes the same sub-values billions of times — it can take seconds. With one decorator line, each `fib(k)` is computed exactly once and the call returns almost instantly. You didn't make the math faster; you made it *happen far fewer times*.

**Batch instead of per-item.** Doing one operation per item often carries fixed overhead each time. Doing it once over all items pays that overhead once:

```go
// SLOW — a string grows by copying its whole contents every += .  O(n²) total.
result := ""
for _, s := range parts {
    result += s            // each += allocates a new, larger string
}

// FAST — accumulate in a builder, produce the final string once.  O(n).
var b strings.Builder
for _, s := range parts {
    b.WriteString(s)       // appends in place, no per-item full copy
}
result := b.String()
```

> **Key insight:** Three questions, in order, before optimizing any computation: *(1) Can I skip it entirely? (2) Can I do it once instead of n times (hoist / memoize)? (3) Can I do it in bulk instead of per-item (batch)?* Only if all three are "no" should you try to make the work itself faster. Eliminating work always beats accelerating it.

---

## Core Concept 5 — The Hot Loop and How to Find It

At the machine level, a CPU does one thing: it executes instructions in a loop, one after another, billions per second. So when a program is CPU-bound, the time is being spent in *some loop* executing *some instructions* over and over. Performance work is largely the art of finding **the hot loop** — the one place where the iteration count and the per-iteration cost multiply into most of your runtime — and shrinking that product.

The math is simple and worth internalizing:

```
loop cost  ≈  (number of iterations)  ×  (work done per iteration)
```

You can attack either factor. Fewer iterations (a better algorithm, Concept 3) or cheaper iterations (less work each pass, Concept 4). A loop running 1,000,000 times doing a tiny bit of needless work — an allocation, a recompile, a redundant lookup — is where junior-level wins hide, because that needless work gets *multiplied a million times*.

This is why **allocating inside a hot loop** is such a classic mistake. Each allocation is cheap in isolation, but multiplied across millions of iterations it dominates:

```go
// SLOW — allocates a fresh slice every iteration; the garbage collector
// then has to clean up millions of throwaway slices.
func sumRows(rows [][]int) int {
    total := 0
    for _, row := range rows {
        buf := make([]int, len(row))   // NEW allocation each iteration
        copy(buf, row)
        total += reduce(buf)
    }
    return total
}

// FAST — allocate the buffer ONCE, reuse it every iteration.
func sumRows(rows [][]int) int {
    total := 0
    var buf []int
    for _, row := range rows {
        buf = buf[:0]                  // reuse the same backing array
        buf = append(buf, row...)
        total += reduce(buf)
    }
    return total
}
```

How do you *find* the hot loop? You already have the tool: the profiler from Concept 2. After `go tool pprof` shows you the top function, `list <funcName>` shows the time spent on each line *inside* it — and the line with the biggest number, almost always inside a loop, is exactly where to focus. Python's `cProfile` plus a line-level profiler (`line_profiler`) does the same. The workflow is always: profile → find the hot function → find the hot line/loop → reduce its iterations or its per-iteration cost.

> **Key insight:** A CPU-bound program's time lives inside a loop, and `cost ≈ iterations × work-per-iteration`. The profiler points you at the loop; then you have exactly two levers — fewer passes or cheaper passes. Anything that wouldn't change one of those two numbers isn't optimization, it's decoration.

---

## Real-World Examples

**1. The dashboard that got slower every month.** A reporting page loaded fine at launch, then crept toward 30 seconds over a year. The team assumed the database was slow (an I/O-bound assumption). A `time` check showed `user` time nearly equal to `real` time — the CPU was pinned. The profiler pointed at a function that, for each of N users, scanned the full list of N transactions: an O(n²) loop hiding in plain sight. As the data grew, n² exploded. Replacing the inner scan with a pre-built map (Concept 3) took the page from 30 seconds back to under a second. The "database problem" was never a database problem.

**2. The image pipeline that allocated itself to death.** A batch image processor spent 60% of its CPU time in garbage collection — visible immediately in the profile. The cause: a buffer allocated fresh inside the per-pixel-row loop, millions of times (Concept 5). Hoisting the allocation out and reusing one buffer cut total runtime by more than half. No algorithm changed; the program simply stopped creating millions of throwaway objects.

**3. The "optimization" that fixed nothing.** A developer was sure a string-formatting function was the bottleneck and spent a day hand-optimizing it. It got 3× faster — and the program's overall runtime didn't move. A profiler, run *afterward*, showed that function accounted for 1.5% of runtime; the real cost was a redundant sort being run inside a loop. A day of work bought a 0.5% improvement. Five minutes with a profiler first would have pointed straight at the sort.

---

## Common Mistakes

1. **Premature optimization — the cardinal sin.** Optimizing code before you've measured that it's slow, or before correctness and clarity are nailed down. You trade readability for speed you may not need, and you almost always optimize the wrong thing. Make it work, make it right, *then* make it fast — and only if a measurement demands it.

2. **Not checking CPU-bound vs I/O-bound first.** Pouring algorithmic effort into a program that's actually waiting on a database. A 100× faster loop saves zero time when the CPU was idle the whole time. Run `time` and watch `user` vs `real` before anything else.

3. **Optimizing without a profiler.** Trusting your gut about where time goes. Your gut is wrong most of the time — even seniors guess wrong. The function you're sure is slow is usually fine; the real cost is somewhere you didn't suspect.

4. **Micro-optimizing while ignoring Big-O.** Caching a length or inlining a call inside an O(n²) loop. You're polishing a brick. Fix the *shape* of the work (the algorithm and data structure) before touching individual lines.

5. **Accidental O(n²).** A nested loop, or calling an O(n) operation (like `x in list`, or `list += ` building a string) *inside* another loop. It looks innocent and runs fine on test data, then collapses in production where n is large. Whenever you see a loop inside a loop, check the complexity.

6. **Allocating inside a hot loop.** Creating a new slice, map, or object every iteration. Cheap once, ruinous a million times — and it loads the garbage collector on top. Allocate once outside the loop and reuse.

7. **Believing "it's fine on my machine."** Your laptop has fast hardware and a small test dataset. Production has more data and shared, contended hardware. Test performance with realistic data sizes, because O(n²) only bites at scale.

---

## Apply it

1. Choose one small, known input for **CPU-Bound Optimization**.
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

- What problem does CPU-Bound Optimization solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
