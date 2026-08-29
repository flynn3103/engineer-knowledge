# CPU Profiling — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **CPU Profiling** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Profiling](../README.md) → CPU Profiling
> *Your program is slow. You have a strong hunch about which function is the culprit. You are almost certainly wrong — and a profiler will prove it to you in about thirty seconds.*

---

## Core Concept 1 — What a CPU Profile Actually Is

A CPU profile answers one question: **of all the CPU time my program used, what fraction went to each function?**

That's it. Not "how many times was `add` called" (that's a different measurement). Not "how long did one request take" (that's a trace). A CPU profile is a **distribution of CPU time across your code**, usually presented as a ranked list:

```
flat  flat%   function
2.41s 38.2%   encoding/json.(*decodeState).object
0.78s 12.4%   runtime.mallocgc
0.51s  8.1%   strings.ToLower
0.22s  3.5%   myapp/orders.processOrder
...
```

Read the first line as: *"38.2% of all the CPU time this program burned was spent inside the JSON object decoder."* That single number is worth more than a week of staring at code. It tells you, unambiguously, that if you want this program to be faster, JSON decoding is where to look — and that `processOrder`, the function you suspected, accounts for a mere 3.5%.

The key property of a profile is that it's **relative and ranked**. You don't usually care about absolute seconds; you care about *proportion*. A function at the top is worth your attention because shrinking it shrinks the whole program. A function near the bottom is not, no matter how ugly its code is.

> **Key insight:** A CPU profile is a *priority list*, not a bug report. It doesn't tell you what's wrong — it tells you where the time is, so you can decide where it's *worth* being right. The whole value is in the ranking.

---

## Core Concept 2 — Sampling: How the Profiler Watches

How does a profiler know that JSON decoding took 38%? There are two strategies, and the one you'll use 95% of the time is **sampling**.

A **sampling profiler** works like a wildlife photographer with a fast shutter. It doesn't follow every animal all day. Instead, at a fixed rate — Go's default is **100 times per second** — it interrupts your program, looks at the current **call stack** (which function is running right now, and who called it), writes that stack down, and lets the program continue. Each interrupt is one **sample**.

```
time →
  sample 1:  main → handleRequest → parseJSON → json.object
  sample 2:  main → handleRequest → parseJSON → json.object
  sample 3:  main → handleRequest → processOrder
  sample 4:  main → handleRequest → parseJSON → json.object
  sample 5:  main → handleRequest → parseJSON → json.scanValue
  ...        (100 of these per second)
```

After running for, say, 6 seconds, the profiler has ~600 stack snapshots. Now it just *counts*. If `json.object` appeared in 229 of 600 samples, then the program was inside `json.object` roughly 229/600 ≈ **38% of the time**. The function seen most often is, by definition, the **hottest**.

This is a beautifully cheap trick. The profiler isn't timing anything — it's taking a statistical poll. The cost of one interrupt is tiny, so sampling adds very little overhead (typically a few percent), which means **the profile reflects how your program really behaves**, not a distorted, slowed-down version of it.

The trade-off is *statistical*: with samples, rare events may be missed, and small numbers are noisy. A function at 0.2% might really be 0.1% or 0.4% — you can't tell from a short run. But a function at 38% is *unmistakably* hot, and that's the one you care about. Sampling is fuzzy at the bottom and razor-sharp at the top, which is exactly where you need it to be.

> **Key insight:** Sampling trades perfect precision for near-zero distortion. It can't reliably measure a function that's 0.1% of the program — but it nails the function that's 40%, and that's the only one worth your time. Cheap-and-honest beats precise-and-misleading.

The other strategy, **instrumentation**, inserts a stopwatch at the entry and exit of *every* function. It's exact about call counts but can slow the program 10–50×, and that slowdown changes which parts dominate — so the profile may no longer describe the real program. Junior rule: **reach for the sampling profiler first.** Every tool below is a sampling profiler by default.

---

## Core Concept 3 — The Golden Rule: Profile, Don't Guess

This is the one law of performance work, and it overrides every instinct you have:

**Do not guess where the time goes. Measure it.**

The reason is empirical and brutal: the hot spot is almost never where you'd guess. There's even a name for the engineering folklore here — **Amdahl's argument** — but you don't need theory. You need one experience of confidently optimising the wrong function to internalise it forever.

Why is intuition so bad at this? A few reasons:

- **The expensive code is invisible.** A single line like `data := strings.ToLower(huge)` or `json.Unmarshal(body, &v)` looks cheap — one function call — but does enormous work inside. Loops *look* expensive; library calls *are* expensive, and they don't look like anything.
- **Call frequency hides in plain sight.** A trivial 5-line function is irrelevant — until you learn it's called 50 million times inside a loop you forgot about. The profiler counts the calls you can't see.
- **You optimise what's satisfying, not what matters.** Rewriting a clever algorithm feels productive. The profiler doesn't care about your feelings; it points at the boring 38% and says "here."

The discipline is simple to state and hard to follow: **before you change a single line for performance, capture a profile. After you change it, capture another and compare.** If you skip the first profile, you're guessing. If you skip the second, you don't actually know your change helped — it might have done nothing, or made things worse.

> **Key insight:** The first profile tells you *where* to work; it routinely contradicts your intuition, and the intuition is what's wrong. The second profile (after your fix) tells you whether the work *helped*. Skip either and you're back to guessing — which is how afternoons disappear into functions that were never the problem.

---

## Core Concept 4 — Reading the Top List: Flat vs Cumulative

Every profiler shows you a **top list** — functions ranked by time. But there are *two* times per function, and confusing them is the single most common beginner mistake. They are **flat** (also called *self*) and **cumulative**.

- **Flat (self) time** = time spent inside *this function's own body*, not counting the functions it calls.
- **Cumulative time** = time spent in this function *plus everything it called* — the entire subtree underneath it.

A picture makes it concrete. Suppose `handleRequest` does almost nothing itself but calls `parseJSON`, which is where the real work happens:

```
function          flat    flat%   cum     cum%
handleRequest     0.02s    0.3%   5.10s   81.0%   ← tiny self, huge cumulative
parseJSON         0.15s    2.4%   4.90s   77.8%
json.object       2.41s   38.2%   3.80s   60.3%   ← big self AND big cumulative
runtime.mallocgc  0.78s   12.4%   0.78s   12.4%   ← leaf: self == cumulative
```

Read it carefully:

- `handleRequest` has **0.3% flat** but **81% cumulative**. It personally does almost nothing — but everything expensive happens *below* it. Optimising `handleRequest`'s own body would be pointless; its body is empty. Its high cumulative just means "the slow stuff is somewhere in here."
- `json.object` has **38% flat** *and* high cumulative. High flat means **the cost is right here, in this function's own code**. This is the one to attack — shrinking its body directly removes 38%.
- `runtime.mallocgc` is a **leaf** (it calls nothing of interest), so its flat and cumulative are equal.

The rule of thumb:

- **Sort by cumulative** to *navigate* — to find which area of the program (which subtree) contains the cost. High cumulative = "the time is in here, keep digging."
- **Sort by flat** to *act* — to find the specific function whose own code you should change. High flat = "the time is *right here*; fix this."

> **Key insight:** Cumulative tells you *which branch* of the program to follow; flat tells you *where to stop and fix*. A function with 90% cumulative and 1% flat is just a corridor — the expensive room is further down. Optimise functions with high **flat** time; use high **cumulative** only to find them.

---

## Core Concept 5 — Capturing Your First Profile

Enough theory. Here's a real, complete first profile in Go — the fastest way to *see* everything above. Suppose you have a benchmark for a function `Tokenize`:

```go
// tokenize_test.go
package text

import "testing"

func BenchmarkTokenize(b *testing.B) {
    input := loadSampleDoc() // a big realistic input
    b.ResetTimer()
    for i := 0; i < b.N; i++ {
        Tokenize(input)
    }
}
```

Run the benchmark and tell Go to write a CPU profile while it runs:

```bash
go test -run=^$ -bench=BenchmarkTokenize -cpuprofile=cpu.out
```

(`-run=^$` skips normal tests so only the benchmark runs.) This produces a file, `cpu.out` — the raw profile. Now open it with `pprof`:

```bash
go tool pprof cpu.out
```

You land in an interactive prompt. Type `top`:

```
(pprof) top
Showing nodes accounting for 5.30s, 92.0% of 5.76s total
      flat  flat%   sum%        cum   cum%
     2.41s 41.8%  41.8%      2.41s 41.8%  text.scanRune
     1.05s 18.2%  60.0%      3.46s 60.0%  text.(*lexer).next
     0.78s 13.5%  73.5%      0.78s 13.5%  runtime.mallocgc
     0.51s  8.9%  82.4%      0.51s  8.9%  unicode.IsLetter
     0.30s  5.2%  87.6%      4.20s 72.9%  text.Tokenize
```

There it is, in five lines. `scanRune` is **41.8% flat** — it's the hot function, and the time is in its own body. `Tokenize` has high *cumulative* (72.9%) but low *flat* (5.2%) — it's the corridor; the work is below it in `scanRune`. And `runtime.mallocgc` at 13.5% is a hint that you're allocating a lot.

Want to know *which lines* inside `scanRune` are hot? Use `list`:

```
(pprof) list scanRune
     2.41s      2.41s    37: for _, r := range s {        // ← most time is on this loop line
         .          .    38:     if r == '\n' {
     0.90s      0.90s    39:         tokens = append(...)  // ← allocation hotspot
```

For a visual call tree in your browser (covered in depth in [Flame Graphs](../04-flame-graphs/junior.md)):

```bash
go tool pprof -http=:8080 cpu.out
```

**Other stacks, same idea.** Every mainstream language has a sampling profiler that produces the same kind of top list and flame graph:

| Stack | Tool | Sampling? |
|---|---|---|
| Go | `go tool pprof` | yes |
| Python | `py-spy` (`py-spy top -- python app.py`) | yes |
| Java / JVM | async-profiler, JFR | yes |
| Linux (any native) | `perf record` / `perf report` | yes |
| macOS | Instruments (Time Profiler) | yes |
| Rust | `cargo flamegraph` | yes |

The tool changes; the mental model — *interrupt, record the stack, count, rank by flat and cumulative* — does not.

> **Key insight:** The hardest part of profiling is starting. Two commands (`go test -cpuprofile`, then `go tool pprof`) and you have a real, ranked answer. Build the reflex: when something is slow, your first move is to capture a profile, not to open the file you suspect.

---

## Real-World Examples

**1. The 38% nobody suspected.** A team's order-import endpoint was slow. Everyone blamed the database query (it *looked* heavy — a big join). The first CPU profile showed the database call at 4% and `json.Unmarshal` at 38% — they were re-parsing a 2 MB config blob on *every* request instead of once at startup. The fix was three lines (parse once, cache it) and cut endpoint CPU by a third. Total time spent guessing about the database beforehand: two days. Time to find the truth with a profile: ninety seconds.

**2. The trivial function called 50 million times.** A Python data job took 40 minutes. `py-spy top` showed 60% of time in a five-line `normalize_key()` helper. The function wasn't slow — it was *called* inside a triple-nested loop, 50 million times, each call re-compiling a regex. Hoisting the regex compile out of the function (compile once, reuse) dropped the job to 9 minutes. No clever code was rewritten; the profile just revealed *frequency* the eye couldn't see.

**3. The satisfying rewrite that did nothing.** A developer spent a day replacing a recursive tree-walk with a slick iterative version "because recursion is slow." The before/after benchmark showed **zero** improvement — the tree-walk was 0.4% of the profile. The actual hot spot, untouched, was string formatting at 31%. This is the cautionary tale behind the golden rule: the change felt productive and measured nothing, because it was never profiled first.

---

## Common Mistakes

1. **Optimising before profiling.** The cardinal sin. You rewrite the function you *suspect*, not the one that's actually hot. The fix is mechanical: capture a profile *first*, every time, even when you're "sure." You're not.

2. **Confusing flat and cumulative.** Seeing `main` or `handleRequest` at 95% cumulative and concluding "the problem is in `main`." It isn't — that's just the top of the tree; *everything* is under `main`. Look at **flat** time to find the function whose own code is expensive.

3. **Optimising the 0.3% function.** Spending a day shaving a function that's a rounding error in the profile, because the change was interesting or satisfying. Apply the 30%/0.3% test: if it's tiny, leave it, no matter how much you want to fix it.

4. **Not comparing before and after.** Making a change and *assuming* it helped. Without a second profile (or benchmark), you don't know — your "optimisation" may have done nothing or regressed. Measure, change, measure again.

5. **Profiling a toy input.** Running the profiler against a 10-row test fixture and trusting the result. With tiny input, startup and fixed costs dominate and the profile lies. Profile with a **realistic, large** workload — the one whose slowness you actually care about.

6. **Trusting tiny percentages.** Treating a 0.2% sampled number as precise. Sampling is statistically noisy at the bottom; that 0.2% could be 0.1% or 0.4%. Only act on numbers that are unambiguously large, or run longer to firm up the small ones.

---

## Apply it

1. Choose one small, known input for **CPU Profiling**.
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

- What problem does CPU Profiling solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
