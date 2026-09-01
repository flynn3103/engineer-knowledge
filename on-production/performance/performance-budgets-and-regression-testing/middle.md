# Performance Budgets and Regression Testing — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Performance Budgets and Regression Testing** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Performance](../README.md) → Performance Budgets and Regression Testing
> *The junior page argued why budgets matter. This page builds the gate: how to pick a threshold that isn't arbitrary, why comparing two benchmark means is a statistical trap, and how `benchstat`, a versioned baseline, and a CI job turn "feels slower" into a pull request that fails for a defensible reason.*

---

## What Makes a Budget Good — Picking the Metric and the Threshold

A budget is a pair: **a metric** and **a threshold**. Both have to be chosen, not guessed.

**Pick the metric that maps to user pain.** Different layers call for different numbers:

| Layer | Metric | Why this one |
|---|---|---|
| Hot function / library | `ns/op`, `allocs/op`, `B/op` | Cheap to measure, deterministic enough to gate per-commit |
| Request handler | p50 / **p99** latency | A mean hides the tail; users feel the tail |
| Service | Throughput (req/s) at a fixed concurrency | Capacity is throughput at a latency you'll accept |
| Web page | Bundle size (gzipped KB), LCP, TBT | Bytes shipped and main-thread block time drive load speed |

- Note what's **missing**: mean response time as a top-level SLO. A mean of 40ms can hide a p99 of 900ms — and the p99 is what a user with a full cart actually experiences. Budget the tail.

**Set the threshold from data, then add headroom.** Three honest ways to pick the number, in order of preference:

1. **Derive it from a requirement.** "The page-load budget is 100ms server-side because the product target is a 1s total load and the frontend owns 900ms of it." This is the only kind of threshold that survives an argument.
2. **Measure the current baseline and forbid getting worse.** "p99 is 45ms today; the budget is 50ms." A *relative* budget — you're protecting the status quo, which is most of what regression testing is.
3. **Set a ceiling from the noise floor.** For microbenchmarks, the threshold is "any change `benchstat` calls statistically significant beyond +N%." N is your tolerance band (often 3–10%), chosen so the gate clears the measurement noise on *your* hardware.

> **Key insight:** A good threshold is one you can *justify in a sentence* — derived from a product requirement, the measured status quo, or the measurement noise floor. If the only justification is "it felt about right," you've built a coin flip that will land red on innocent PRs until someone deletes the check.

---

## The Core Problem — You Cannot Compare Two Means

Here is the trap that sinks naive perf gates:

- You run the benchmark on `main`, get **120 ns/op**. You run it on the PR branch, get **123 ns/op**. That's +2.5% — a regression?
- Almost certainly **not**. A single benchmark run is one sample from a noisy distribution. Run the *identical* code twice and you'll routinely see the mean wobble by a few percent, driven by:
  - **CPU frequency scaling** — the core boosts or throttles depending on temperature and load.
  - **Co-tenancy** — on a CI runner, your benchmark shares the box with other jobs.
  - **Memory layout luck** — allocator and cache state differ between runs.
  - **Garbage collection timing** — a GC cycle landing inside the measured window adds a spike.

```
run 1 of unchanged code:  118 ns/op
run 2 of unchanged code:  124 ns/op   ← +5%, and nothing changed
run 3 of unchanged code:  120 ns/op
```

- If your gate is `candidate_mean > baseline_mean * 1.03`, run 2 fails the build for a change that doesn't exist. You'd ship a gate that flakes on its own noise.
- The fix: **take multiple samples of each version and ask whether the difference is statistically significant** — larger than the spread you'd expect from noise alone. A +2.5% shift where each version's runs swing ±5% is indistinguishable from luck. A +25% shift where runs swing ±1% is real. The mean alone can't tell these apart; you need the *variance* too.

> **Key insight:** A benchmark result is a distribution, not a number. The entire job of a regression gate is to separate *signal* (a real change in the distribution) from *noise* (the same distribution sampled twice) — and that is a statistics problem, not an arithmetic one.

---

## benchstat — Significance, Not Just a Delta

`benchstat` (from `golang.org/x/perf`) does this comparison correctly for Go benchmarks. Give it **multiple runs** of a baseline and **multiple runs** of a candidate; it computes the median of each, the spread, and a **p-value** for whether they differ.

Collect samples with `-count`:

```bash
# 10 samples of each version, saved to files
git checkout main
go test -run='^$' -bench=BenchmarkParse -count=10 ./parser > old.txt

git checkout my-feature
go test -run='^$' -bench=BenchmarkParse -count=10 ./parser > new.txt

# compare
benchstat old.txt new.txt
```

- `-run='^$'` disables unit tests so only benchmarks run. `-count=10` gives `benchstat` enough samples to estimate the spread.

Reading the output is the skill:

```
                │   old.txt   │             new.txt              │
                │   sec/op    │   sec/op     vs base             │
Parse-8           120.4n ± 2%   122.1n ± 3%        ~ (p=0.481 n=10)
Encode-8          88.30n ± 1%   97.55n ± 2%   +10.48% (p=0.000 n=10)
geomean           103.1n        109.2n         +5.79%
```

Decode every column:

- **`120.4n ± 2%`** — the **median** time per op and the spread (here ±2% around the median). If the `±` is large, your environment is too noisy to gate on.
- **`~ (p=0.481 n=10)`** — the tilde means **no statistically significant change**. `Parse` moved +1.4% in the mean, but with p=0.481 that's well inside the noise. **A `~` is a pass.** Do *not* fail the build on it.
- **`+10.48% (p=0.000 n=10)`** — a **real** regression. p=0.000 says the chance this is noise is effectively zero. **This is what your gate should catch.**
- **`geomean`** — the geometric mean across all benchmarks, a single rollup number.

The convention: `benchstat` only prints a percentage delta when the change is significant (by default p < 0.05); otherwise it prints `~`. That single rule — **fail on a printed delta, pass on `~`** — is the heart of a non-flaky gate.

You can also gate on allocations, which are *deterministic* and therefore far easier than time:

```
                │  old.txt   │            new.txt             │
                │ allocs/op  │ allocs/op   vs base            │
Encode-8          4.000 ± 0%   7.000 ± 0%  +75.00% (p=0.000 n=10)
```

- Allocs have `± 0%` spread — they don't jitter — so an allocs/op regression is unambiguous. Many teams gate on `allocs/op` *first* because it's the cheapest reliable signal.

> **Key insight:** `benchstat` turns "is this slower?" into "is this *significantly* slower?" A printed `%` delta is a finding; a `~` is a non-event.

---

## The Baseline — Golden Numbers, Versioned

`benchstat` compares two files, so a regression gate needs a **baseline**: the "before" numbers to compare the PR against. Two sources:

**Option A — compute the baseline in CI from the merge target.**
- On every PR, check out the base branch (`main`), run the benchmarks, save `old.txt`, then check out the PR head, run again, save `new.txt`, and `benchstat` the two.
- Most robust: both runs happen on the **same runner, back to back**, cancelling out most hardware variance. Cost: double the benchmark time per PR.

**Option B — store golden numbers in the repo.**
- Commit a `bench/baseline.txt` (or a JSON of per-benchmark medians) tied to a known-good commit. The PR runs benchmarks once and compares against the committed file.
- Cheaper, but fragile: the baseline was measured on a *different* machine at a *different* time, so the noise floor is wider and you'll need a looser tolerance.
- When you intentionally accept a perf change, regenerate and commit the file — the diff becomes a reviewable record of "we got 8% faster here on purpose."

```
repo/
  bench/
    baseline.txt        ← golden numbers, regenerated on intentional changes
    README.md           ← "how to regenerate: make bench-baseline"
```

```makefile
bench-baseline:
	go test -run='^$$' -bench=. -count=10 ./... > bench/baseline.txt
	@echo "Baseline updated. Commit bench/baseline.txt with a note WHY it changed."
```

- In practice, **Option A is the default** for microbenchmark gates (same-runner comparison kills variance).
- **Option B** is used when benchmarks are too slow to run twice per PR, or for tracking long-term trends across releases.

> **Key insight:** A baseline measured on a *different machine* than the candidate is comparing apples to a slightly different apple — hardware variance pollutes the delta. Whenever you can, measure baseline and candidate **on the same runner, in the same job**, so the only systematic difference between them is the code.

---

## Wiring the Gate into CI

A complete, working GitHub Actions job using Option A (same-runner baseline). It checks out `main`, benchmarks it, checks out the PR, benchmarks it, and uses `benchstat` to fail only on a *significant* regression.

```yaml
# .github/workflows/perf.yml
name: perf-regression
on: pull_request

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0          # need history to check out the base branch

      - uses: actions/setup-go@v5
        with:
          go-version: '1.22'

      - name: Install benchstat
        run: go install golang.org/x/perf/cmd/benchstat@latest

      - name: Benchmark base (main)
        run: |
          git checkout ${{ github.event.pull_request.base.sha }}
          go test -run='^$' -bench=. -benchmem -count=10 ./... > /tmp/old.txt

      - name: Benchmark candidate (PR)
        run: |
          git checkout ${{ github.event.pull_request.head.sha }}
          go test -run='^$' -bench=. -benchmem -count=10 ./... > /tmp/new.txt

      - name: Compare
        run: |
          benchstat /tmp/old.txt /tmp/new.txt | tee /tmp/result.txt

      - name: Fail on significant regression
        run: |
          # benchstat prints a "+N%" delta ONLY when significant.
          # Fail if any sec/op or allocs/op regressed past the tolerance band.
          python3 scripts/check_regression.py /tmp/result.txt --tolerance 5
```

The gate logic lives in a small script rather than a fragile shell one-liner, because you want a **tolerance band** (don't fail on a significant but tiny +1% — only on changes past, say, +5%) and a clear failure message:

```python
# scripts/check_regression.py
import re, sys, argparse

p = argparse.ArgumentParser()
p.add_argument("file"); p.add_argument("--tolerance", type=float, default=5.0)
a = p.parse_args()

# match lines like:  Encode-8  88.30n ± 1%  97.55n ± 2%  +10.48% (p=0.000 n=10)
delta_re = re.compile(r"^(\S+)\s+.*?([+-]\d+\.\d+)%\s+\(p=")
regressions = []
for line in open(a.file):
    m = delta_re.match(line)
    if m and float(m.group(2)) > a.tolerance:     # positive = slower
        regressions.append((m.group(1), float(m.group(2))))

if regressions:
    print("PERF REGRESSION beyond +%.1f%% tolerance:" % a.tolerance)
    for name, pct in regressions:
        print("  %-20s +%.2f%%" % (name, pct))
    sys.exit(1)
print("No significant regression beyond tolerance. OK.")
```

Two design choices make this gate trustworthy rather than annoying:

1. **It only looks at lines `benchstat` flagged significant** (lines with a `±%` delta, not `~`). Noise is filtered by `benchstat` before the script ever sees it.
2. **It has a tolerance band on top of significance.** A change can be statistically real and still operationally irrelevant (+1.2% on a function called twice at startup). The band lets you say "real *and* big enough to care about."

---

## Fighting Flakiness — Median, Relative Thresholds, Retry

Even with `benchstat`, CI runners are hostile measurement environments. Hardening tactics, in order of impact:

- **Use the median, never a single run.** `-count=10` and `benchstat`'s median already do this. One run is a coin flip; ten runs and a median is a measurement. Never gate on `-count=1`.
- **Gate on relative deltas, not absolute numbers.** "Fail if slower than 120 ns/op" breaks the moment you move from a fast runner to a slow one — the absolute number is hardware-specific. "Fail if more than 5% slower than the base branch *on this same runner*" travels across hardware unchanged.
- **Pin the runner and quiet the box.** Use a consistent `runs-on` (don't mix runner classes). For serious gates, a dedicated, isolated runner with frequency scaling disabled cuts `±%` dramatically. The wider your noise floor (`± 8%` vs `± 1%`), the larger a regression has to be before `benchstat` can detect it.
- **Retry the comparison, not just the test.** Re-running the *whole comparison* (fresh baseline + candidate) on a borderline result is legitimate — you're taking a new measurement, not p-hacking a green build. What is *not* legitimate: re-running until it passes and ignoring the failures. If it fails 2 of 3 times, it's a regression.
- **Prefer allocs/op for the strict gate.** Allocations are deterministic (`± 0%`), so an `allocs/op` budget never flakes — make it a hard gate; treat `ns/op` as a softer, wider-tolerance gate.

> **Key insight:** Flakiness is not bad luck — it's a noise floor wider than the regression you're trying to detect. Fight it two ways: **shrink the noise** (more samples, quieter runner, deterministic metrics like allocs) and **widen the signal you require** (relative thresholds with a tolerance band). A gate is only as sensitive as `regression_size > noise_floor`.

---

## Frontend Budgets — Lighthouse CI, size-limit, bundlesize

The same discipline applies to the browser, where the budgets are **bytes shipped** and **time to interactive**. Bundle size is *deterministic* — a given build always produces the same byte count — so size gates never flake.

**size-limit** — enforce a gzipped/brotli byte budget per entry point:

```json
// package.json
{
  "size-limit": [
    { "path": "dist/main.js", "limit": "180 KB" },
    { "path": "dist/vendor.js", "limit": "120 KB" }
  ],
  "scripts": { "size": "size-limit" }
}
```

```yaml
# in CI
- run: npm run build
- run: npx size-limit          # exits non-zero if any bundle exceeds its limit
```

- `bundlesize` does the same job with a similar config; `size-limit` additionally estimates download+execution time, not just bytes.
- Either one turns "the bundle quietly grew 60 KB over six PRs" into a single PR that fails the moment it crosses the line.

**Lighthouse CI** — budget the *runtime* metrics (LCP, Total Blocking Time, performance score) by running Lighthouse against a built preview:

```js
// lighthouserc.js
module.exports = {
  ci: {
    collect: { url: ['http://localhost:3000/'], numberOfRuns: 5 },
    assert: {
      assertions: {
        'categories:performance': ['error', { minScore: 0.9 }],
        'largest-contentful-paint': ['error', { maxNumericValue: 2500 }],
        'total-blocking-time': ['warn', { maxNumericValue: 300 }],
      },
    },
  },
};
```

```yaml
- run: npm run build && npm start &
- run: npx @lhci/autorun
```

- `numberOfRuns: 5` — Lighthouse metrics are noisy (they involve a real browser), so it runs multiple times and takes the median, exactly like `benchstat` does for Go.
- The split between `error` (fail the build) and `warn` (report only) is the frontend equivalent of a tolerance band: hard-fail on the metrics you've committed to, warn on the ones you're watching.

> **Key insight:** Frontend budgets divide cleanly into **deterministic** (bundle bytes — gate hard, no statistics needed) and **noisy runtime** (LCP, TBT — needs multiple runs and a median, same as a Go microbenchmark). Bundle-size gates are the cheapest, most reliable perf gate any web team can add; do that one first.

---

## Worked Example — A Real Regression Caught in CI

A PR refactors a JSON encoder to be "cleaner." The author runs the gate locally before pushing:

```bash
git stash                                                   # stash the refactor
go test -run='^$' -bench=BenchmarkEncode -benchmem -count=10 ./codec > old.txt
git stash pop                                               # restore it
go test -run='^$' -bench=BenchmarkEncode -benchmem -count=10 ./codec > new.txt
benchstat old.txt new.txt
```

```
                │   old.txt    │              new.txt              │
                │    sec/op     │    sec/op      vs base            │
Encode-8           1.842µ ± 1%    2.431µ ± 2%    +31.97% (p=0.000 n=10)

                │   old.txt    │              new.txt              │
                │  allocs/op    │  allocs/op     vs base            │
Encode-8           6.000 ± 0%    14.00 ± 0%     +133.3% (p=0.000 n=10)
```

- The story is unambiguous: the "cleaner" version is **32% slower** and allocates **more than twice** as much, both with `p=0.000` — confirmed by the deterministic `± 0%` on allocs.
- The refactor moved a buffer from the stack to the heap. In CI, `scripts/check_regression.py` sees `+31.97%` past the 5% tolerance and fails:

```
PERF REGRESSION beyond +5.0% tolerance:
  Encode-8             +31.97%
```

The PR goes red with a specific, defensible reason. The author reuses a pooled buffer, re-runs, and gets:

```
Encode-8           1.842µ ± 1%    1.798µ ± 2%        ~ (p=0.214 n=10)
```

- A `~` — no significant change from baseline. The gate passes.
- The contrast is the whole point: the *same gate*, on the *same code path*, correctly fails the 32% regression and correctly ignores the −2.4% wobble, because it reasons about significance instead of comparing two bare means.

---

## Common Mistakes

1. **Comparing two single runs.** `120` vs `123` from one run each is noise. Always `-count=10` (or more) and let `benchstat` judge significance. A `-count=1` gate is a random number generator wired to your CI status.
2. **Failing the build on a `~` result.** `~` means *no significant change*. A gate that goes red on it will fire on innocent PRs and get disabled. Only fail on a printed `%` delta past your tolerance.
3. **Absolute thresholds across different hardware.** "Fail if > 120 ns/op" passes on your laptop and fails on the slower CI runner for no real reason. Gate on *relative* change versus a same-runner baseline.
4. **Comparing a baseline measured on a different machine/time.** Hardware and co-tenancy variance leak straight into the delta. Measure baseline and candidate back-to-back on the same runner whenever you can.
5. **No tolerance band on top of significance.** A change can be statistically real and operationally irrelevant (+1% on a cold-path function). Require *significant **and** past N%* before failing, or you'll block PRs over rounding.
6. **Gating only on the mean, ignoring the tail.** A budget on mean latency can pass while p99 doubles. Budget the percentile users actually feel (p99), not the average that hides the tail.
7. **Re-running until green.** Re-measuring a borderline result is fine; ignoring 2-of-3 failures because the 3rd passed is p-hacking. If it regresses more often than not, it regressed.

---

## Apply it

1. Find a real component where **Performance Budgets and Regression Testing** affects an interface or dependency.
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

- Which boundary is most affected by Performance Budgets and Regression Testing?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
- Where would you set a budget's threshold — what's a principled answer beyond "10% slower than today"?
- Why is a Student's t-test usually the wrong tool for comparing benchmark results?
- What's the difference between statistical significance and effect size, and why does a gate need both?
- Why does keeping all raw measurements matter, not just a summary statistic?
- Why is a relative comparison more trustworthy than an absolute number from CI?
