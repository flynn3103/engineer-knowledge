# Performance Budgets and Regression Testing — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Performance Budgets and Regression Testing** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Performance](../README.md) → Performance Budgets and Regression Testing
> *Nobody ever ships a commit titled "make the app 400ms slower." Slowness arrives one harmless-looking millisecond at a time, and by the time anyone notices, the cause is spread across two hundred commits and nobody can find it.*

---

## Core Concept 1 — Performance Rots Silently

**Performance degrades by default, and it does so invisibly.** Unlike a crash or a wrong answer:

- A slowdown produces no error, no stack trace, no red build. It just *is*, and it grows.
- Every feature adds *something*, and "something" costs time: a validation check, an extra query, a bigger payload, a logging call in a hot loop.
- None of these are bugs — each is a reasonable trade, a feature for a few milliseconds. The problem is purely *additive math*: a hundred reasonable trades is a feature-rich app that is unusably slow.

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

- No single step looks alarming. You can't point to *the* commit that ruined it — there isn't one.
- By the time the slowness is *felt*, the cause is *distributed* across hundreds of changes, and bisecting through them is miserable.
- The cure is **not** a heroic optimization sprint once a year — that only buys back ground you'll lose again.
- The cure is to **catch each cut at the moment it's made**, while the cause is a single PR you can see, review, and reject. A 12ms regression is trivial to find when it's the only change in the diff, and nearly impossible to find buried under six months of unrelated work.

> **Key insight:** You can't fight an enemy you can't see. Performance regression testing exists to make slowdowns *visible at the moment they're introduced*, when fixing them is cheap, instead of *visible only in aggregate*, when fixing them is a project.

---

## Core Concept 2 — A Budget Turns a Vague Goal Into a Testable Line

"The app should be fast" is a wish, not a goal:

- You cannot test it, cannot fail a build on it, and three engineers will have three different ideas of what "fast" means.
- A **performance budget** replaces the wish with a *number*:
  - "The search endpoint's **p99 latency must stay under 200ms**."
  - "The homepage's **JavaScript bundle must stay under 250KB** (gzipped)."
  - "Parsing one request must use **fewer than 40 allocations**."
  - "The checkout flow must complete in **under 1.5 seconds** on a mid-range phone."

Why a number matters:

- "Fast" can't fail a build; `p99 < 200ms` can. Once a budget is written down, "is this PR acceptable?" stops being opinion and becomes measurement.
- A budget **makes the cost of a feature explicit at decision time.** Example: bundle budget is 250KB, you're at 240KB, a new feature wants a 30KB chart library.
  - Without a budget: the library gets added, nobody notices, the page is now 270KB and slower for everyone — forever.
  - With a budget: adding it blows the limit, the build fails, and the team has a real conversation — is the chart worth the speed? Maybe yes, but now it's a *choice*, not an accident.
- A budget doesn't forbid spending — it forces spending to be *deliberate*. You're allowed to go over budget; you just have to *raise the budget on purpose*, in a commit, with a reason.

> **Key insight:** A budget converts "fast" (an opinion no test can check) into "under N" (a line every test can check). The number doesn't have to be perfect — almost any reasonable line beats no line, because *a line is the only thing CI can enforce*.

---

## Core Concept 3 — A Regression Test Is Just a Test That Fails When Things Get Slower

You already trust regular tests. A unit test asserts `add(2, 3) == 5`. A **performance regression test** is the same idea pointed at *speed* instead of *correctness*: it measures how long something takes (or how much it allocates), and **fails if that number is worse than allowed.**

Smallest possible version, a Go benchmark:

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

Reading that line: each call to `Search` took **~22,841 ns (~23µs)**, used **4096 bytes**, made **37 allocations**. Those three numbers are exactly what you'd put a budget on. Turn the benchmark into a *failing test* — a hard ceiling that breaks the build if crossed:

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

- If a PR pushes `Search` from 37 to 45 allocations, *this test goes red*, in *that PR*, naming the problem.
- The author sees it immediately, while the cause is the only thing in their diff.
- There is nothing more sophisticated going on — you've given speed the same red-build guardian that correctness has always had.

> **Key insight:** A performance regression test is not exotic. It is an ordinary test whose assertion happens to be `measured_cost <= budget` instead of `output == expected`.

---

## Core Concept 4 — Baselines: Comparing New Against Known-Good

A fixed budget like "`< 40 allocs`" has a weakness:

- It only catches you when you cross the *absolute* line. If you're at 37 and a PR pushes you to 39, the budget of 40 is happy — yet you just absorbed a real regression, and the *next* small PR will tip you over with no warning.

The stronger approach is a **baseline**: a saved record of the *known-good* measurement, so you compare *new vs. previous* rather than *new vs. some far-off ceiling*. The rule becomes "this PR may not be meaningfully slower than `main` is *today*."

In Go, the standard tool for this comparison is `benchstat`:

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

- `+18.9%` is the regression, stated plainly, *with a confidence value* (`p=0.000` means it's almost certainly real, not random noise).
- Notice `±2%` and `n=10` — they exist because timing is **noisy**. A single run can be off by several percent from OS scheduling, CPU frequency scaling, or warm/cold caches.
- Run it *multiple times* (`-count=10`) and let the tool decide signal vs. noise. A baseline comparison without repeated runs will fire false alarms constantly and teach the team to ignore it.

The practical pattern most teams land on combines both ideas:

- An **absolute budget** as a hard backstop ("never exceed 250KB, period") — catches cumulative drift.
- A **baseline comparison** with a small tolerance ("don't regress more than ~5% versus `main`") — catches the individual cut.

> **Key insight:** An absolute budget asks "are we still under the ceiling?" A baseline asks "did *this change* make things worse?" You want both — and *neither* is meaningful without enough repeated runs to separate a real regression from random timing noise.

---

## Core Concept 5 — Wiring It Into CI

A regression test that only runs when someone remembers is worthless. The value is unlocked when it runs **automatically on every pull request.**

Stripped-down GitHub Actions job that fails the build on a performance regression:

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

- For the simplest possible version — no baseline file at all — the hard-ceiling test from Concept 3 needs *zero* extra setup: `go test ./...` already runs it, and CI already runs `go test`. That's the easiest place to start.

Two warnings about CI environments specifically:

1. **Shared CI runners are noisy.** They're VMs sharing hardware with other jobs, so absolute timings bounce around far more than on your laptop. Trust *relative* changes and *allocation counts* (deterministic, don't drift with CPU load) more than raw wall-clock time.
2. **Make the failure message actionable.** "Benchmark failed" teaches people to retry the build; "`Search` regressed +18.9% (22.8µs → 27.1µs), budget is +5%" teaches them to look at their own diff.

> **Key insight:** The discipline only works when it's *automatic and unavoidable*. A check that runs on every PR and blocks merge is a guardian; a check that runs "when you remember" is a suggestion, and suggestions lose to deadlines every single time.

---

## Real-World Examples

**1. The web page that gained 400ms over a year.**
- A marketing site loads in 1.1s at launch. Over twelve months the team adds an A/B testing script, a chat widget, a heavier hero image, three font weights, and an analytics bundle.
- Each addition was approved; each was small. The site now loads in 2.4s and conversions are down.
- Fix: a **bundle-size budget** enforced in CI (`total JS < 250KB`, `largest image < 200KB`). The next 90KB widget fails the build, and the team decides on purpose whether it's worth the speed.

**2. The allocation that quietly tripled GC pressure.**
- A Go service handles 10k requests/sec comfortably. A refactor changes a request parser to build strings with `+` in a loop instead of reusing a buffer — clean-looking code, all tests green.
- Latency at p99 creeps up over the following weeks as the extra garbage drives the garbage collector harder.
- With a regression test asserting `allocs/op <= 40` on the parser, this never ships: the PR that raised allocations from 37 to 58 goes red on the author's screen, named, in their diff. Allocation counts are *deterministic*, so this check is rock-solid even on noisy CI.

**3. The "fast on my Mac" trap.**
- An engineer optimizes a query and it's blazing on their M-series laptop, so they ship. In production — on older, busier servers — it's slower than before, because their fast local machine hid the regression.
- A budget defined as an *absolute number checked in CI* (not "feels fast for me") catches this, because CI runs on a consistent, neutral environment.
- The lesson: "fast on my machine" is the performance cousin of "works on my machine" — the cure is the same: measure somewhere neutral and automatic.

---

## Common Mistakes

1. **Having a goal instead of a budget.** "It should be fast" can't fail a build. Write a *number* (`p99 < 200ms`), or you have nothing CI can check.
2. **Only checking absolute limits, never deltas.** A hard ceiling of 40 allocs lets you creep from 37 to 39 unnoticed — until one more PR tips you over with no warning. Add a baseline comparison.
3. **Benchmarking once and trusting the number.** Timing is noisy. Run multiple times (`-count=10`) and use a tool like `benchstat` to separate signal from noise, or you'll get false alarms and learn to ignore the check.
4. **Trusting wall-clock time on shared CI runners.** Cloud runners share hardware, so absolute timings bounce wildly. Lean on *allocation counts* and *relative deltas* instead of raw nanoseconds.
5. **A vague failure message.** "Benchmark failed" teaches people to hit retry. State *what* regressed, *by how much*, and *against what budget*.
6. **Running the check only locally / only sometimes.** A guardian that depends on someone remembering will be skipped on the busy day that matters most. Wire it into CI on every PR.
7. **Treating the budget as sacred and never raising it.** Budgets are *deliberate spending limits*, not laws of nature. Raise the budget *on purpose*, in a commit, with a reason, when a feature is worth the cost.

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
- Why do you need an automated performance gate at all — can't you just profile when things feel slow?
- What does it mean to treat a performance budget as a "testable line," and why does that framing matter?
- What are the four broad categories of things you'd put a performance budget on?
- Why budget allocations when users only feel latency?
- How does a performance budget relate to an SLO?
