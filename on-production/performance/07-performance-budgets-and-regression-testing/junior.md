# Performance Budgets and Regression Testing — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Performance Budgets and Regression Testing** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Performance](../README.md) → Performance Budgets and Regression Testing
> *Nobody ever ships a commit titled "make the app 400ms slower." Slowness arrives one harmless-looking millisecond at a time, and by the time anyone notices, the cause is spread across two hundred commits and nobody can find it.*

---

## Core Concept 1 — Performance Rots Silently

The central fact you must internalize: **performance degrades by default, and it does so invisibly.** Unlike a crash or a wrong answer, a slowdown produces no error, no stack trace, no red build. It just *is*, and it grows.

Why does it grow? Because every feature you add does *something*, and "something" costs time. A new validation check. An extra database query. A larger payload. A logging call in a hot loop. None of these are bugs. Each is a deliberate, reasonable trade — a feature for a few milliseconds. The problem is purely *additive math*: a hundred reasonable trades is a feature-rich app that is unusably slow.

Picture the curve over a year:

```
latency
  600ms |                                          ____
        |                                    _____/
        |                              _____/
  300ms |                       ______/
        |              _______/
   80ms |____________/
        +--------------------------------------------------> time / commits
         v1                                          today
        "fast"        each PR: +5..20ms          "why is it so slow?"
```

No single step looks alarming. Slide your eye along the line and you can't point to *the* commit that ruined it — there isn't one. This is what makes it so dangerous and so hard to fix after the fact: by the time the slowness is *felt*, the cause is *distributed* across hundreds of changes, and bisecting through them is miserable.

The cure is not heroic optimization sprints once a year (which only buy back ground you'll lose again). The cure is to **catch each cut at the moment it's made**, while the cause is a single PR you can see, review, and reject. A 12ms regression is trivial to find and fix when it's the only change in the diff. It is nearly impossible to find when it's buried under six months of unrelated work.

> **Key insight:** You can't fight an enemy you can't see. The entire discipline of performance regression testing exists to make slowdowns *visible at the moment they're introduced*, when fixing them is cheap, instead of *visible only in aggregate*, when fixing them is a project.

---

## Core Concept 2 — A Budget Turns a Vague Goal Into a Testable Line

"The app should be fast" is not a goal. It is a wish. You cannot test it, you cannot fail a build on it, and three engineers will have three different ideas of what "fast" means. A **performance budget** replaces the wish with a *number*:

- "The search endpoint's **p99 latency must stay under 200ms**."
- "The homepage's **JavaScript bundle must stay under 250KB** (gzipped)."
- "Parsing one request must use **fewer than 40 allocations**."
- "The checkout flow must complete in **under 1.5 seconds** on a mid-range phone."

The magic of a budget is not the number itself — it's that a number is *testable*. "Fast" can't fail a build; `p99 < 200ms` can. The moment you write a budget down, the question "is this PR acceptable?" stops being a matter of opinion and becomes a matter of measurement. Either the number is under the line or it isn't.

A budget also does something subtle and valuable: it **makes the cost of a feature explicit at decision time**. Imagine a budget of 250KB on your bundle and you're at 240KB. A new feature wants to add a 30KB chart library. Without a budget, that library gets added, nobody notices, and the page is now 270KB and slower for everyone — forever. *With* a budget, adding it blows the limit, the build fails, and the team has a real conversation: do we want this chart more than we want a fast page? Maybe yes! But now it's a *choice* someone made on purpose, not an accident that happened to everyone.

That is the whole point. A budget doesn't forbid spending — it forces spending to be *deliberate*. You're allowed to go over budget; you just have to *raise the budget on purpose*, in a commit, with a reason. The slowness can't sneak in.

> **Key insight:** A budget converts "fast" (an opinion no test can check) into "under N" (a line every test can check). The number doesn't have to be perfect — almost any reasonable line is infinitely better than no line, because *a line is the only thing CI can enforce*.

---

## Core Concept 3 — A Regression Test Is Just a Test That Fails When Things Get Slower

You already trust regular tests. A unit test asserts `add(2, 3) == 5`; if a change breaks that, the test fails and the build is red. A **performance regression test** is the exact same idea pointed at *speed* instead of *correctness*: it measures how long something takes (or how much it allocates), and **fails if that number is worse than allowed.**

Here's the smallest possible version using a Go benchmark. Go has benchmarking built into its test tooling, which makes it the friendliest place to start. A benchmark is a function that runs your code `b.N` times so the tool can measure it precisely:

```go
// search_test.go
package search

import "testing"

func BenchmarkSearch(b *testing.B) {
    index := buildTestIndex() // set up once, not measured
    b.ResetTimer()
    for i := 0; i < b.N; i++ {
        Search(index, "performance budget")
    }
}
```

Run it and Go reports timing and memory:

```bash
$ go test -bench=BenchmarkSearch -benchmem
BenchmarkSearch-8    52310    22841 ns/op    4096 B/op    37 allocs/op
```

Read that line: each call to `Search` took about **22,841 nanoseconds** (~23µs), used **4096 bytes**, and made **37 allocations**. Those three numbers are exactly the kind of thing you put a budget on. Now turn the benchmark into a *failing test* — a hard ceiling that breaks the build if crossed:

```go
func TestSearchAllocBudget(t *testing.T) {
    index := buildTestIndex()
    const budget = 40 // allocs/op — our committed limit

    result := testing.Benchmark(func(b *testing.B) {
        for i := 0; i < b.N; i++ {
            Search(index, "performance budget")
        }
    })

    if got := result.AllocsPerOp(); got > budget {
        t.Fatalf("alloc regression: %d allocs/op exceeds budget of %d", got, budget)
    }
}
```

Now if some innocent-looking PR pushes `Search` from 37 to 45 allocations, *this test goes red*, in *that PR*, with a message that names the problem. The author sees it immediately, while the cause is the only thing in their diff. That is the entire mechanism — there is nothing more sophisticated going on. You've given speed the same red-build guardian that correctness has had all along.

> **Key insight:** A performance regression test is not a special, exotic thing. It is an ordinary test whose assertion happens to be `measured_cost <= budget` instead of `output == expected`. Once you see that, "guarding performance in CI" stops sounding hard and starts sounding like Tuesday.

---

## Core Concept 4 — Baselines: Comparing New Against Known-Good

A fixed budget like "`< 40 allocs`" is a great start, but it has a weakness: it only catches you when you cross the *absolute* line. If you're at 37 and a PR pushes you to 39, the absolute budget of 40 is happy — yet you just absorbed a real regression, and the *next* small PR will tip you over with no warning. The thousand cuts can still get you; they just have to be quieter.

The stronger approach is a **baseline**: a saved record of the *known-good* measurement, so you compare *new vs. previous* rather than *new vs. some far-off ceiling*. The rule becomes "this PR may not be meaningfully slower than `main` is *today*," which catches the 37→39 creep that an absolute budget misses.

In Go, the standard tool for this comparison is `benchstat`. You save the current good numbers, then compare your branch against them:

```bash
# 1. On main: capture the baseline
$ git checkout main
$ go test -bench=. -benchmem -count=10 > baseline.txt

# 2. On your branch: capture the new numbers
$ git checkout my-feature
$ go test -bench=. -benchmem -count=10 > new.txt

# 3. Compare — benchstat tells you what actually changed
$ benchstat baseline.txt new.txt
name       old time/op    new time/op    delta
Search-8     22.8µs ± 2%    27.1µs ± 3%   +18.9%  (p=0.000 n=10+10)
```

That `+18.9%` is the regression, stated plainly, *with a confidence value* (`p=0.000` means it's almost certainly a real change, not random noise). Notice the `±2%` and `n=10` — they exist because timing is **noisy**. A single benchmark run can be off by several percent purely due to the OS scheduling other work, CPU frequency scaling, or caches being warm or cold. That's why you run it *multiple times* (`-count=10`) and let the tool decide whether a difference is signal or noise. A baseline comparison without repeated runs will fire false alarms constantly and teach the team to ignore it — the worst outcome.

The practical pattern most teams land on combines both ideas: an **absolute budget** as a hard backstop ("never exceed 250KB, period") *and* a **baseline comparison** with a small tolerance ("don't regress more than ~5% versus `main`"). The budget catches the cumulative drift; the baseline catches the individual cut.

> **Key insight:** An absolute budget asks "are we still under the ceiling?" A baseline asks "did *this change* make things worse?" You want both: the ceiling stops slow accumulation, the baseline catches each fresh cut — and *neither* is meaningful without enough repeated runs to separate a real regression from random timing noise.

---

## Core Concept 5 — Wiring It Into CI

A regression test that only runs when someone remembers to run it locally is worthless — it depends on the one human who is busiest at the moment. The value is unlocked the instant it runs **automatically on every pull request**, so the check happens whether anyone remembers or not. That's what CI is for.

Conceptually, the CI step is identical to running your normal tests, plus a comparison against the saved baseline. Here's a stripped-down GitHub Actions job that fails the build on a performance regression:

```yaml
# .github/workflows/perf.yml
name: performance
on: [pull_request]

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with: { go-version: '1.22' }

      - name: Run benchmarks (this branch)
        run: go test -bench=. -benchmem -count=10 ./... > new.txt

      - name: Compare against committed baseline
        run: |
          go install golang.org/x/perf/cmd/benchstat@latest
          benchstat baseline.txt new.txt | tee result.txt
          # fail if any benchmark regressed beyond tolerance
          ./scripts/check_regression.sh result.txt   # exits non-zero on a bad delta
```

For the simplest possible version — no baseline file at all — the hard-ceiling test from Concept 3 needs *zero* extra setup: it's an ordinary Go test, so `go test ./...` already runs it, and CI already runs `go test`. The budget is enforced for free. That's the easiest place to start: write one `TestXxxBudget` with an absolute limit, and you have a real performance guardian today.

Two warnings about CI environments specifically. First, **shared CI runners are noisy** — they're virtual machines sharing hardware with other jobs, so absolute timings bounce around far more than on your laptop. This is exactly why baseline-with-tolerance and repeated runs matter so much in CI: trust *relative* changes and *allocation counts* (which are deterministic and don't drift with CPU load) more than raw wall-clock time. Second, **make the failure message actionable.** "Benchmark failed" teaches people to retry the build; "`Search` regressed +18.9% (22.8µs → 27.1µs), budget is +5%" teaches them to look at their own diff.

> **Key insight:** The discipline only works when it's *automatic and unavoidable*. A check that runs on every PR and blocks merge is a guardian; a check that runs "when you remember" is a suggestion, and suggestions lose to deadlines every single time.

---

## Real-World Examples

**1. The web page that gained 400ms over a year.** A marketing site loads in 1.1s at launch. Over twelve months the team adds an A/B testing script, a chat widget, a heavier hero image, three font weights, and an analytics bundle. Each addition was approved; each was small. The site now loads in 2.4s and conversions are down. The fix going forward is a **bundle-size budget** enforced in CI (`total JS < 250KB`, `largest image < 200KB`): the *next* time someone adds a 90KB widget, the build fails and the team decides on purpose whether the widget is worth the speed. The thousand cuts stop because each cut now has to justify itself.

**2. The allocation that quietly tripled GC pressure.** A Go service handles 10k requests/sec comfortably. A refactor changes a request parser to build strings with `+` in a loop instead of reusing a buffer — clean-looking code, all tests green. Latency at p99 creeps up over the following weeks as the extra garbage drives the garbage collector harder. With a regression test asserting `allocs/op <= 40` on the parser, this never ships: the PR that raised allocations from 37 to 58 goes red on the author's screen, named, in their diff. Allocation counts are *deterministic*, so this check is rock-solid even on noisy CI.

**3. The "fast on my Mac" trap.** An engineer optimizes a query and it's blazing on their M-series laptop, so they ship. In production — on older, busier servers — it's slower than before, because their fast local machine hid the regression. A budget defined as an *absolute number checked in CI* (not "feels fast for me") catches this, because CI runs on a consistent, neutral environment rather than the fastest machine on the team. The lesson: "fast on my machine" is the performance cousin of "works on my machine," and the cure is the same — measure somewhere neutral and automatic.

---

## Common Mistakes

1. **Having a goal instead of a budget.** "It should be fast" can't fail a build, so nothing enforces it and performance drifts. Write a *number* (`p99 < 200ms`), or you have nothing CI can check.

2. **Only checking absolute limits, never deltas.** A hard ceiling of 40 allocs lets you creep from 37 to 39 unnoticed — until one more PR tips you over with no warning. Add a baseline comparison to catch the small cuts the ceiling misses.

3. **Benchmarking once and trusting the number.** Timing is noisy; a single run can be off by several percent for reasons unrelated to your code. Run multiple times (`-count=10`) and use a tool like `benchstat` to separate signal from noise — or you'll get false alarms and learn to ignore the check.

4. **Trusting wall-clock time on shared CI runners.** Cloud runners share hardware, so absolute timings bounce wildly. Lean on *allocation counts* and *relative deltas* (which are stable) rather than raw nanoseconds, or your build will fail randomly.

5. **A vague failure message.** "Benchmark failed" teaches people to hit retry. State *what* regressed, *by how much*, and *against what budget*, so the author knows it's their diff and what to fix.

6. **Running the check only locally / only sometimes.** A guardian that depends on someone remembering will be skipped on the busy day that matters most. Wire it into CI on every PR so it's automatic and blocks merge — that's the whole point.

7. **Treating the budget as sacred and never raising it.** Budgets are *deliberate spending limits*, not laws of nature. Sometimes a feature is worth the cost — then raise the budget *on purpose*, in a commit, with a reason. The goal is conscious choices, not zero spending.

---

## Apply it

1. Choose one small, known input for **Performance Budgets and Regression Testing**.
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

- What problem does Performance Budgets and Regression Testing solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
