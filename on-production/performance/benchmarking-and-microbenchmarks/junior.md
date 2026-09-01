# Benchmarking and Microbenchmarks — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Benchmarking and Microbenchmarks** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Performance](../README.md) → Benchmarking and Microbenchmarks
> *"It feels faster" is not data. A benchmark turns a feeling into a number, and a number into something you can defend, compare, and watch over time.*

---

## Core Concept 1 — A Benchmark Is a Controlled Measurement

A benchmark has three jobs, and all three matter:

1. **Run the target code** — the thing you want to know about.
2. **Measure** something objective — time, operations per second, bytes allocated.
3. **Be repeatable** — run it again and get *roughly* the same answer.

The word doing the heavy lifting is **controlled**:

- A measurement you can't reproduce isn't a benchmark — it's an anecdote.
- Timing something once, getting "42 ms," and moving on teaches you almost nothing.
- You don't know if the true value is 40 ms or 80 ms, or whether the 42 was a fluke caused by your laptop indexing files in the background.

Go bakes this discipline into the standard library. A benchmark is just a function starting with `Benchmark`, taking a `*testing.B`:

```go
package strutil

import "testing"

func BenchmarkConcat(b *testing.B) {
    for i := 0; i < b.N; i++ {
        _ = "hello" + "world"
    }
}
```

The key piece is `b.N`:

- You do **not** pick how many times to run the code — the framework does.
- It runs your loop a few times, sees how long that took, then automatically scales `b.N` up (1, then 100, then 10,000, then millions) until the total run is long enough to measure reliably.
- You write the loop; Go decides the iteration count so the result is statistically meaningful.

Run it:

```bash
go test -bench=BenchmarkConcat
```

```
goos: darwin
goarch: arm64
pkg: example/strutil
BenchmarkConcat-8    1000000000    0.31 ns/op
PASS
```

Read that last line:

- The benchmark ran **one billion** iterations, and each one averaged **0.31 nanoseconds**.
- The `-8` is the number of CPUs available (`GOMAXPROCS`).
- You didn't ask for a billion runs — Go chose that many *because* the operation is so fast that it needed a huge sample to get a stable per-operation figure.

> **Key insight:** the value of a benchmark is not the single number it prints — it's that the number is *reproducible* and *comparable*. A benchmark exists so you can run it before a change and after a change and ask "did this actually help?" One run in isolation answers nothing.

---

## Core Concept 2 — Micro vs Macro Benchmarks

Benchmarks come in two sizes, and confusing them is one of the most common ways people fool themselves.

A **microbenchmark** measures one tiny thing in isolation — a single function, a parsing routine, one hot loop. It answers a narrow question:

> *"Of these two ways to write this exact function, which is faster?"*

```go
// Microbenchmark: which string-building approach wins?
func BenchmarkBuilder(b *testing.B) {
    for i := 0; i < b.N; i++ {
        var sb strings.Builder
        for j := 0; j < 100; j++ {
            sb.WriteString("x")
        }
        _ = sb.String()
    }
}
```

A **macrobenchmark** measures a whole, realistic operation — an entire HTTP request, a full report generation, processing a real input file end to end. It answers a broader question:

> *"How fast is the thing the user actually waits for?"*

```go
// Macrobenchmark: the whole request path, the way production runs it
func BenchmarkHandleRequest(b *testing.B) {
    srv := newServer(testDB)         // real router, real handlers
    req := httptest.NewRequest("GET", "/api/orders/42", nil)
    b.ResetTimer()                   // don't count the setup above
    for i := 0; i < b.N; i++ {
        w := httptest.NewRecorder()
        srv.ServeHTTP(w, req)
    }
}
```

Both are useful, but they answer different questions, and **a microbenchmark win does not guarantee a macrobenchmark win.**

- You can make a string function 3× faster in a microbenchmark and see zero measurable effect on request latency — because that function was 0.1% of the request's time.
- This is the gap between *"fast in a loop"* and *"fast in production."*

| | Microbenchmark | Macrobenchmark |
|---|---|---|
| Scope | One function / loop | A whole operation / request |
| Question | "Which implementation is faster?" | "Is the user-visible thing fast enough?" |
| Speed to run | Very fast (ns–µs) | Slower (ms–s) |
| Risk | Optimising something that doesn't matter | Hard to isolate *what* is slow |
| Use it to | Compare two candidate functions | Decide if the system meets its target |

> **Key insight:** start macro to find *what* is slow (or use a [profiler](../profiling/cpu-profiling/junior.md)), then go micro to fix the specific hot spot — and finally return to the macro benchmark to confirm the fix actually moved the number that matters. A microbenchmark in a vacuum optimises code that may be completely irrelevant to real performance.

---

## Core Concept 3 — Why Naive Timing Lies

The instinct of every beginner is to wrap a stopwatch around the code:

```go
start := time.Now()
result := slowFunction()
fmt.Println(time.Since(start))   // "237µs" — done, right?
```

This is wrong in at least four ways, and each one alone can make the number meaningless.

**1. One run is noise, not signal.**
- Your machine is doing a hundred other things — the OS scheduler, background processes, your editor indexing.
- A single measurement captures whatever happened to be going on *that instant*.
- Run the same code three times and you might see 237µs, 198µs, 410µs. Which is "the" answer? None of them — you need many runs and their *distribution*.

**2. The clock is too coarse for tiny code.**
- If `slowFunction()` takes 4 nanoseconds and your timer's resolution is ~50 nanoseconds, you're measuring the *clock*, not the code.
- This is why you can't time a single fast operation directly — you must run it millions of times and divide, which is exactly what `b.N` does for you.

**3. The compiler may delete your code.** This is the sneaky one.
- If you compute a result and never use it, an optimising compiler is allowed to conclude the work is pointless and **remove it entirely** — a process called dead-code elimination (DCE).
- Your "benchmark" then measures an empty loop:

```go
// BROKEN: result is never used → the compiler may delete the call
func BenchmarkParse(b *testing.B) {
    for i := 0; i < b.N; i++ {
        parse(input)   // looks measured; may be optimised to nothing
    }
}
// Result: 0.25 ns/op — suspiciously fast. That's the smell of DCE.
```

The fix is to *use* the result so the compiler can't prove it's dead — typically by assigning to a package-level variable the compiler can't see through:

```go
var sink Result   // package-level: compiler can't assume it's unused

func BenchmarkParse(b *testing.B) {
    for i := 0; i < b.N; i++ {
        sink = parse(input)   // result escapes; the work must really happen
    }
}
```

**4. Print-and-eyeball gives no notion of confidence.**
- Printing one number tells you nothing about how much it varies, so you can't tell a real 5% improvement from random jitter.
- You end up "confirming" wins that don't exist.

> **Key insight:** naive timing — one run, a wall clock wrapped around a tiny op, print and eyeball — produces a number that *looks* authoritative and is frequently false. A real benchmarking tool exists precisely to handle iteration count, clock resolution, dead-code elimination, and variance *for you*. Reaching for `time.Now()` to "quickly check" is how confident, wrong conclusions are born.

---

## Core Concept 4 — Warm-Up and Steady State

Code is often *slower the first time it runs* and faster afterward.

- If you measure that first slow run, you measure a cost the user rarely pays.
- The first few runs are the **warm-up**; the stable speed they settle into is the **steady state**.

Why does code speed up after a few runs?

- **Caches fill up.** The CPU pulls the relevant data and instructions into its fast caches; the first run pays the "cold cache" penalty, later runs don't.
- **Just-In-Time (JIT) compilation** (huge in **Java** and the JVM, and in JavaScript). The first runs execute slow interpreted bytecode; once the JIT notices a hot loop, it compiles it to optimised machine code and subsequent runs are *dramatically* faster.
- **One-time setup** — lazy initialisation, connection pools, file-system caches warming.

This matters most in Java:

- A naive JMH-less timing loop in Java can show a function getting 10× faster partway through purely because the JIT kicked in.
- That's why the JVM benchmarking tool **JMH** runs explicit warm-up iterations (which it *discards*) before it starts measuring:

```java
@Warmup(iterations = 5)            // 5 runs, thrown away, to let the JIT compile
@Measurement(iterations = 10)      // 10 runs that actually count
@Benchmark
public void parse() { /* ... */ }
```

Go is ahead-of-time compiled, so it has no JIT warm-up:

- Caches still need warming, and there's almost always **setup** you must keep out of the measurement.
- That's what `b.ResetTimer()` is for: do the expensive one-time preparation, then reset the clock so only the loop is timed.

```go
func BenchmarkSearch(b *testing.B) {
    data := buildBigIndex()   // slow setup — should NOT be counted
    b.ResetTimer()            // start the clock fresh, here
    for i := 0; i < b.N; i++ {
        _ = data.Search("target")
    }
}
```

> **Key insight:** the number you usually care about is the **steady-state** number — the speed code runs at *after* it has warmed up, because that's the speed it runs at in production for the millionth request. Measure the cold first run and you report a cost the user almost never pays. Warm up, *then* measure.

---

## Core Concept 5 — Variance: Read the Spread, Not One Number

Here is the rule that separates people who benchmark from people who *think* they benchmark: **never trust a single number — look at how much the numbers vary.**

- Run the same benchmark twice and you will get slightly different results, because your machine is noisy.
- The question is never "what was the number?" — it's "what was the number, *plus or minus how much*?"
- A measurement of `200 ns/op ± 2%` is solid. A measurement of `200 ns/op ± 40%` is mush, and any "improvement" smaller than that 40% swing is invisible noise.

Go makes this easy with `-count`, which runs each benchmark several times so you can see the spread:

```bash
go test -bench=Search -count=10 | tee old.txt
```

```
BenchmarkSearch-8    523 ns/op
BenchmarkSearch-8    519 ns/op
BenchmarkSearch-8    641 ns/op    ← an outlier; the machine hiccuped
BenchmarkSearch-8    521 ns/op
BenchmarkSearch-8    525 ns/op
...
```

Eyeballing ten numbers is better than one, but you still shouldn't judge "is my change faster?" by hand. Use **benchstat**, which runs the statistics for you and refuses to call a change real unless it survives the noise:

```bash
# Measure before and after a change, then compare
go test -bench=Search -count=10 > old.txt
# ... make your optimisation ...
go test -bench=Search -count=10 > new.txt
benchstat old.txt new.txt
```

```
name      old time/op    new time/op    delta
Search-8     524ns ± 1%     310ns ± 2%   -40.84%  (p=0.000 n=10+10)
```

Two things to read here:

- The `± 1%` and `± 2%` are the **variance** — small, so the measurements are trustworthy.
- The `p=0.000` is a confidence figure: it means the difference is statistically real, not luck.
- When benchstat instead prints `~ (p=0.21)`, it's telling you *"the change is within the noise — I can't say it did anything."* That honesty is the entire point.

> **Key insight:** a benchmark result is a *range*, not a point. The discipline is to run many times, look at the spread, and only believe an improvement that is clearly bigger than the noise. "It went from 524 ns to 519 ns" is not an improvement — it's the machine breathing. Let a tool like benchstat decide what's real; your eyes are too eager to see wins.

---

## Real-World Examples

**1. The rewrite that "felt faster" and wasn't.**
- A developer replaces a `for`-loop string concatenation with a fancier approach because "it should be faster."
- They time it once before (190µs) and once after (170µs), declare victory, and merge.
- Run under benchstat with `-count=10`, the truth emerges: `~ (p=0.34)` — the change is pure noise, the two versions are identical within variance, and the "20µs improvement" was the machine hiccuping.
- A single before/after measurement had manufactured a win that didn't exist.

**2. The microbenchmark that optimised the wrong thing.**
- A team spends two days making a date-formatting function 4× faster, with a beautiful microbenchmark to prove it.
- The macrobenchmark of the actual API request? Unchanged.
- A [profile](../profiling/cpu-profiling/junior.md) later shows date formatting was 0.3% of request time; the real cost was a database query.
- The micro win was real *and* irrelevant — a textbook case of "fast in a loop, no effect in production."

**3. The benchmark the compiler deleted.**
- Someone benchmarks a hashing function, sees `0.4 ns/op`, and excitedly reports that the hash is "basically free."
- It wasn't — the result was never used, so dead-code elimination removed the call and the benchmark timed an empty loop.
- Assigning the result to a package-level `sink` variable brought the honest number back: `38 ns/op`, a hundred times slower.
- The "free" hash was a measurement artifact, not a fact.

---

## Common Mistakes

1. **Measuring once and trusting it.** A single run captures whatever noise was present that instant. Always run many times (`-count=10`) and look at the variance before believing any number.

2. **Wrapping `time.Now()` around a tiny operation.** The clock is too coarse for nanosecond work, and you'll measure the clock, not the code. Use a proper harness (`testing.B`, `timeit`, JMH) that loops and divides.

3. **Letting dead-code elimination delete the work.** If the benchmarked result is never used, the compiler may remove it and you'll time an empty loop. Assign the result to a package-level `sink` (Go) or use the tool's "blackhole" (JMH's `Blackhole`).

4. **Counting setup in the measurement.** Building the test fixture inside the timed loop inflates every result. Move setup out and call `b.ResetTimer()` (Go) so only the work-under-test is timed.

5. **Forgetting warm-up — especially on the JVM.** In Java, the first runs are slow interpreted code; measure those and you'll under-report steady-state speed by an order of magnitude. Discard warm-up iterations (JMH does this for you).

6. **Believing a micro win is a macro win.** Making one function faster proves nothing about end-to-end speed. Confirm with a macrobenchmark or profile that the function was actually on the hot path.

7. **Calling tiny differences "improvements."** "524 ns → 519 ns" is noise, not a win. If the change is smaller than the variance, it isn't real — let benchstat's `p`-value decide.

---

## Apply it

1. Choose one small, known input for **Benchmarking and Microbenchmarks**.
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

- What problem does Benchmarking and Microbenchmarks solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
- Why benchmark instead of just reasoning about which code should be faster?
- What's the difference between a benchmark and a profile?
- A microbenchmark reports 0.3 ns/op for real work — what almost certainly happened?
- Why does the first iteration of a benchmark often report a misleading time?
- Why isn't a single timed measurement enough to trust a benchmark result?
- What does Go's `b.N` represent, and who decides its value?
