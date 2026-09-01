# Performance Budgets and Regression Testing — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Performance Budgets and Regression Testing** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Performance](../README.md) → Performance Budgets and Regression Testing
> *The middle page taught you to set a budget and write a benchmark that fails when it's exceeded. This page is about the hard part nobody warns you about: a benchmark that fails when nothing changed. Real performance signals are buried in noise, you run hundreds of them at once, and the machine you measure on lies to you. This is the statistics and systems of regression detection that actually holds up in CI.*

---

## The Statistical Core — "Did It Get Slower?" Is a Hypothesis Test

A benchmark does not produce *a* number. It produces a *sample* drawn from a noisy distribution — GC pauses, scheduler preemption, cache state, frequency scaling, and neighbor processes all perturb each iteration.

- The real question is never "is run B's number bigger than run A's?" It's: **could the difference between sample A and sample B plausibly arise from noise alone?** That's a two-sample hypothesis test, with the null hypothesis "A and B come from the same distribution."

**Why not a t-test (Student's / Welch's)?**

- The t-test assumes the samples are approximately normal and compares *means*.
- Benchmark latency distributions are emphatically not normal: right-skewed, with a hard floor (you can't run faster than the work allows) and a long tail of slow outliers (a GC pause, a context switch).
- A few tail samples drag the mean and inflate the variance, so a mean-based test is both biased and underpowered on exactly the data you have. You can sometimes rescue a t-test by working in log-space or trimming, but that's patching the wrong tool.

**Use a non-parametric rank test.**

- The **Mann-Whitney U test** (equivalently the Wilcoxon rank-sum test) makes no distributional assumption. It pools all measurements from both samples, ranks them, and asks whether values from sample B systematically rank higher (slower) than values from sample A.
- Because it operates on *ranks*, a single 50ms outlier counts the same as a value just above the median — it can't hijack the result. This is the right default for "did latency shift?"
- Its paired cousin, the **Wilcoxon signed-rank test**, applies when measurements are naturally paired (e.g., the same input run on old and new binaries back-to-back).

> **Key insight:** Latency is skewed and outlier-ridden, so test *ranks*, not *means*. Mann-Whitney U asks "do new-version measurements systematically outrank old-version ones?" — a question that survives GC pauses and scheduler noise that would wreck a t-test.

**Significance is not the same as size — and size is what you gate on.**

- With enough samples, Mann-Whitney will report a vanishingly small p-value for a 0.2% difference that no user will ever feel. A p-value answers "is the difference real?"; it says nothing about "is the difference *big enough to care about*?"
- Two practical effect-size measures:
  - The **median (or percentile) shift**: `Δ = median(B) − median(A)`, reported as a percentage. This is what humans reason about and what a budget is written in.
  - **Common-language effect size** (the U statistic normalized): the probability that a random measurement from B is slower than a random one from A. 0.5 means no difference; 0.9 means B is almost always slower.
- A robust gate combines both: **require statistical significance (p below threshold) *and* an effect size above a meaningful floor.** Significance alone floods you with trivial "regressions"; effect size alone fires on noise.

This is exactly what Go's **benchstat** does — it takes multiple runs of `go test -bench` from each side, applies the Mann-Whitney U test, and prints the median delta only when the difference is significant:

```bash
# Collect MULTIPLE runs per side — one run is statistically useless.
git checkout main
go test -run='^$' -bench=BenchmarkParse -count=10 ./... > old.txt
git checkout feature
go test -run='^$' -bench=BenchmarkParse -count=10 ./... > new.txt

benchstat old.txt new.txt
```

```
name      old time/op    new time/op    delta
Parse-8     412µs ± 2%     418µs ± 3%    ~     (p=0.347 n=10+10)
Encode-8    1.83ms ± 1%    2.09ms ± 1%   +14.2% (p=0.000 n=10+10)
```

- `Parse` shows a 1.5% nominal increase but `~` and `p=0.347` — **not significant**, indistinguishable from noise, do nothing.
- `Encode` shows `+14.2%` with `p=0.000` — a real, large regression.
- The `± 2%` is the sample's coefficient of variation; benchstat needs `n` of at least ~6–10 per side to have the power to call anything. Feeding it `-count=1` makes its test meaningless: it cannot estimate variance from a single point.
- JMH (Java) gives you the raw material rather than a built-in delta test: run with enough forks and iterations and it reports confidence intervals (`Score Error (99.9%)`); you then run the same statistical comparison across two builds. The discipline is identical — many samples, compare distributions, gate on significance *and* size.

---

## The Multiple-Comparisons Problem — Why 500 Benchmarks Drown You in False Positives

Here is the failure that kills most homegrown performance gates:

- Run a test at the conventional **α = 0.05** significance level: a 5% chance of a false positive *per test* when nothing actually changed. One benchmark: 5% risk, fine. Run 500 benchmarks on a commit that changed nothing:

```
P(at least one false alarm) = 1 − (1 − 0.05)^500 ≈ 1 − 0.95^500 ≈ 1.0
```

- You will get roughly **25 false "regressions" on every clean commit** (0.05 × 500). The gate is now noise. People learn to ignore it within a week, and a muted gate catches nothing. This is the **multiple-comparisons problem**, and at scale it is the dominant reason performance CI is distrusted.

Two standard corrections, controlling two different things:

**Bonferroni — control the family-wise error rate (FWER).**
- To keep the probability of *any* false positive across the whole family at 0.05, test each benchmark at `α / m` where `m` is the number of tests: `adjusted α = 0.05 / 500 = 0.0001`.
- Dead simple, guarantees FWER ≤ 0.05, but brutally conservative when `m` is large — requiring p < 0.0001 means you'll miss many genuine moderate regressions (poor statistical power). Fine for a handful of critical benchmarks; the wrong tool for 500.

**Benjamini-Hochberg — control the false discovery rate (FDR).**
- This is what you want at scale. Instead of "never any false positive," BH controls the *expected proportion of false positives among the things you flagged*. Flag 20 regressions at FDR = 0.05, you accept that ~1 of them is likely spurious — a far more useful contract, and far more powerful. Procedure:

```
1. Run all m tests, collect p-values p_1 … p_m.
2. Sort ascending: p_(1) ≤ p_(2) ≤ … ≤ p_(m).
3. Find the largest k such that  p_(k) ≤ (k / m) · Q   where Q is your target FDR (e.g. 0.05).
4. Reject (flag as regression) all hypotheses 1 … k.
```

- Concretely, with `m = 500` and `Q = 0.05`: the smallest p-value is compared against `(1/500)·0.05 = 0.0001`, the second against `0.0002`, and so on up to the 500th against `0.05`. A benchmark with a genuinely large regression and `p = 0.000` clears the bar easily; marginal `p = 0.04` noise hits that would each individually "pass" α = 0.05 are correctly suppressed because they don't clear their position-adjusted threshold.

> **Key insight:** Running many benchmarks at α = 0.05 *guarantees* a flood of false positives — at 500 benchmarks you average ~25 phantom regressions per clean commit. You must correct for multiplicity. Use **Bonferroni** for a small set of critical gates; use **Benjamini-Hochberg FDR** for large suites.

- A practical refinement: also require a minimum effect size *before* a benchmark even enters the multiple-comparison pool. A 0.3% shift that's "significant" is noise you don't want spending your FDR budget. Filter on effect size, then apply BH to what's left.

---

## Change-Point Detection — Regressions in a Noisy Time Series

Pairwise A/B (compare PR branch to base) is the right model for a single change reviewed in isolation. It breaks down for a continuously-built `main`:

- A regression often isn't a clean step; it's a small shift that hides under run-to-run variance on any single comparison but is obvious over 50 commits.
- Noise on a busy CI fleet drifts (a kernel upgrade, a new runner generation), so "compare to the immediately preceding commit" fires constantly on environment changes, not code changes.
- Many tiny regressions accumulate. No single PR trips a threshold; the curve slopes upward for a month.

The better mental model for `main` is a **noisy time series per benchmark**, and the question is: **at which commit did the level of the series change?** That's **change-point detection**, a fundamentally different, more robust formulation than pairwise testing.

- **E-divisive means** is the approach MongoDB built its production system on (open-source **Hunter** / DSI signal-processing tooling). Non-parametric, hierarchical: it finds the single point in the series that best splits it into two segments with the most different distributions (using an energy-distance statistic that, like Mann-Whitney, doesn't assume normality), then recurses into each segment, accepting a split only if a permutation test says it's significant. Output: statistically justified change points — "the p50 of `insert_throughput` shifted down 6% at commit `a3f9c1`" — even when no single adjacent pair of commits showed a clear difference. Robust to long, flat, noisy stretches that defeat pairwise comparison.

```
series:  ████████▁▁▁▁▁▁▁▁         ← E-divisive finds the ONE point where the
         ^^^^^^^^         ^^^^^^^^   distribution shifts, not 14 noisy pairwise diffs
                 ↑ change point (regression here)
```

Two simpler classics, useful to know and sometimes enough:

- **CUSUM (cumulative sum):** track the running sum of deviations from the expected mean; when the cumulative sum drifts past a control limit, you've detected a sustained shift. Excellent at catching *small persistent* regressions that a per-point threshold misses, because it integrates the signal over time. Cheap, online, and battle-tested in industrial process control.
- **Sliding-window median (or robust rolling baseline):** maintain the median (not mean — median resists outliers) of the last `N` builds; flag when the current build sits a robust number of MADs (median absolute deviations) above that window. Simple, interpretable, and a solid first system before you reach for E-divisive.

> **Key insight:** On a continuously-built branch, the right question is "where did the level shift?" (change-point detection over the series) not "is this commit slower than the last one?" (pairwise). Pairwise drowns in run-to-run noise and environment drift; change-point detection surfaces the real step changes and the slow accumulating slopes that pairwise can never see.

---

## A Stable Measurement Environment — Why Cloud CI Defeats Microbench Regression Detection

All the statistics in the world cannot extract a 3% regression signal from a measurement environment with 20% variance. **The variance of your runner sets the noise floor, and the noise floor sets the smallest regression you can ever detect.** This is the single most underappreciated fact in performance CI, and it's where most efforts silently fail.

Shared cloud CI runners are *adversarial* to microbenchmark stability:

- **Noisy neighbors:** you share a physical host with other tenants whose load you can't see or control. CPU steal time, memory-bandwidth contention, and shared-cache eviction inject variance with no relationship to your code.
- **Frequency scaling and turbo:** the CPU boosts and throttles based on thermal and power state. The same loop runs at 3.8 GHz cold and 2.9 GHz after thirty seconds of work. Turbo on a shared box is non-deterministic.
- **Heterogeneous hardware:** "the runner" is actually a random draw from several CPU generations. Comparing a number from a Skylake runner to one from an Ice Lake runner is comparing two different machines.
- **Virtualization jitter:** the hypervisor preempts your vCPU at moments you can't observe, producing fat-tailed latency that no amount of sampling averages away.

The result: on shared cloud CI, microbenchmark run-to-run variance routinely sits at **10–30%**. With that noise floor, you cannot reliably detect anything smaller than a ~15–20% regression — and most real regressions are 3–8%. The gate is statistically incapable of its job, regardless of how good the math downstream is.

**The fix, in order of strength:**

1. **Dedicated bare-metal runners**, isolated from the rest of CI, doing nothing else while a benchmark runs. This alone often takes variance from ~20% to ~2%.
2. **Pin everything that scales:** disable turbo/frequency scaling (`cpupower frequency-set -g performance`, or fix the frequency), pin the benchmark to specific cores and away from housekeeping cores (`taskset` / `cset shield`), disable hyperthread siblings on the benchmark cores, set the process to a real-time-ish priority, disable ASLR for determinism, and quiet background daemons.

```bash
# Linux: prepare a core for stable measurement
sudo cpupower frequency-set -g performance          # no on-demand scaling
echo 0 | sudo tee /sys/devices/system/cpu/cpu7/topology/.../online   # park HT sibling
sudo cset shield --cpu 6 --kthread on               # isolate CPU 6 from kernel threads
sudo taskset -c 6 chrt -f 99 ./benchmark            # pin to core 6, FIFO priority
```

3. **The relative-comparison-same-host workaround** — the most important trick when you *cannot* get pristine hardware. Don't compare today's absolute number against a historical absolute number from a different machine. Instead, **build both the baseline and the candidate, and run them alternated, back-to-back, on the same runner in the same job.** Interleave them (A B A B A B …) so any slow drift in the host's state (thermal creep, a neighbor waking up) hits both sides roughly equally and cancels in the *difference*. You give up the absolute number but recover a *relative* delta that's stable even on a noisy box, because the shared environment is common-mode noise that subtracts out.

> **Key insight:** Statistics can't beat physics. A 20%-variance cloud runner has a noise floor of ~15–20%, so it is *physically incapable* of detecting the 3–8% regressions you actually care about. Either get dedicated, pinned, bare-metal runners — or, if you can't, measure baseline and candidate *alternated on the same host in the same job* so the host's noise is common-mode and cancels in the delta.

---

## Calibrating the Gate — The False-Positive vs False-Negative Trade

Every detector trades two errors:

- **False positive (false alarm):** flag a regression that isn't real. The gate fails a clean PR.
- **False negative (miss):** fail to flag a real regression. Slow code ships.

These trade off against the **detection threshold**. Tighten it (require a bigger, more-significant change to fire) and you cut false positives but raise false negatives. Loosen it and the reverse. There's no setting that eliminates both; there's only the right balance for your blast radius.

- The balance is asymmetric in a way that matters: **a flaky gate gets disabled.** This is the iron law of performance CI. A gate that fails clean PRs even 5% of the time will, within weeks, be muted, marked non-blocking, or routed around with a retry — at which point it catches *nothing*. A few false positives don't cost you a few false positives; they cost you the entire gate. So a *blocking* gate's default posture leans toward fewer false positives (a higher firing threshold), accepting that the smallest regressions slip through, because the alternative is no gate at all.

**Calibrate the tolerance to the measured noise floor — don't guess it.** Derive the threshold from data:

1. Run the benchmark suite repeatedly on the *same commit* (no code change) on your actual runner — say 30 times.
2. Measure the empirical run-to-run distribution per benchmark: its median absolute deviation, its p95–p99 swing. That's your noise floor for that benchmark on that hardware.
3. Set the firing threshold comfortably above that floor — e.g., at the p99 of the no-change distribution, or median + k·MAD with k chosen to hit a target false-positive rate. A benchmark whose no-change swing is ±2% might gate at +6%; one whose floor is ±10% can only honestly gate at +25% (and you should fix its stability or demote it to non-blocking trend-only).

This makes the per-benchmark threshold *individual* — quiet benchmarks gate tightly, noisy ones loosely — which is far better than one global "+5%" that's too strict for noisy benchmarks and too loose for quiet ones.

A two-tier system resolves the false-positive/false-negative tension well:

- **Blocking gate:** conservative, low false-positive threshold (per-benchmark p99 of noise + a real effect-size floor + multiple-comparison correction). Fires rarely, trusted, blocks merge. Tuned to almost never cry wolf.
- **Non-blocking trend alarm:** sensitive change-point detection over the history (E-divisive / CUSUM) that posts to a dashboard or a channel but doesn't block. Catches the slow 1%/month creep and the marginal regressions the blocking gate deliberately lets through. Humans triage these; no individual one halts the pipeline.

> **Key insight:** A flaky gate doesn't cost you a few false alarms — it costs you the whole gate, because the team will mute it. Derive the threshold from the *measured* noise floor of each benchmark on the actual runner, keep the blocking gate conservative enough to be trusted, and put the sensitive detection in a non-blocking trend alarm.

---

## Automatic Bisection — Finding the Commit That Did It

Detection tells you a regression entered the tree *somewhere* between two known-good and known-bad builds — often a range of dozens of commits if benchmarks run nightly rather than per-commit. Manually re-running a flaky benchmark across 40 commits is exactly the toil to automate. **`git bisect run` driven by a benchmark** does it in `O(log n)` builds.

The mechanics are standard bisection, but the *predicate* is the interesting part. `git bisect` expects a script that exits 0 for "good" and 1 for "bad" — but a benchmark doesn't return good/bad, it returns a noisy number. So the bisect script must itself run the statistical comparison:

```bash
#!/usr/bin/env bash
# bisect-perf.sh — git bisect predicate for a benchmark regression.
set -euo pipefail

go build ./... || exit 125          # 125 = "skip": this commit won't build, not good/bad

# Run enough samples for the test to have power; compare against a pinned baseline.
go test -run='^$' -bench=BenchmarkEncode -count=12 ./pkg/codec > /tmp/cur.txt

# benchstat exits nonzero only if the median is SIGNIFICANTLY worse than baseline
# beyond the calibrated effect-size threshold.
if perf-compare --baseline /tmp/good-baseline.txt \
                --candidate /tmp/cur.txt \
                --metric "BenchmarkEncode" \
                --threshold-pct 8 --alpha 0.01 ; then
  exit 0    # good: not significantly slower than baseline
else
  exit 1    # bad: regression present at this commit
fi
```

```bash
git bisect start
git bisect bad   HEAD              # nightly that detected the regression
git bisect good  v2.7.0           # last known-good build
git bisect run ./bisect-perf.sh   # automatically walks log2(range) commits
```

Three senior points that make this actually work:

- **Use `exit 125` for unbuildable/irrelevant commits** so bisect *skips* them instead of mislabeling — without this, a refactor commit that doesn't compile poisons the search.
- **The predicate must be statistically robust**, not a single-sample threshold. A flaky predicate makes `git bisect` confidently converge on the *wrong* commit — bisection has no error correction; one mislabeled step sends it down the wrong half of the tree permanently. Run enough samples (and, ideally, the alternated same-host comparison) inside the predicate.
- **Run it on the stable, pinned runner.** Bisecting a microbenchmark on a noisy cloud box is throwing dice 6 times in a row and trusting the product.

Chromium's perf bots and MongoDB's DSI both automate this culprit-finding step — once a change point is detected over the series, an automated bisection narrows the change-point range down to the single offending commit and files it. The detection identifies the *range*; bisection identifies the *commit*.

---

## Macro/Load Regression vs Micro — Two Different Statistical Regimes

Microbenchmarks and macro/load tests are not the same problem wearing different sizes — they're statistically distinct, and conflating them causes bad gates.

- **Microbenchmarks** isolate one function or hot loop. Cheap, repeatable, thousands of iterations, so you get a large sample and tight per-sample noise *if* the environment is stable. Their danger is *relevance*: a 30% regression in a function that's 0.1% of real traffic is noise to the system. Statistics: the Mann-Whitney / benchstat machinery above — many fast samples, distribution comparison.
- **Macro / load tests** drive the whole system under representative load (a fixed-rate request generator, a replayed production trace) and measure end-to-end metrics: throughput at fixed latency, p50/p95/p99 latency at fixed throughput, error rate. Expensive (minutes to hours), so you get *few* samples — sometimes one full run per build — which inverts the statistical situation:
  - You can't lean on large-`n` significance testing; with `n = 1` run per side, your "sample" is the *distribution of per-request latencies within one run*, and run-to-run variance is often the dominant, unmeasured term.
  - The metrics are **tail percentiles**, which are themselves high-variance estimators — p99 from one run is a far noisier number than the median, so naive thresholding on p99 false-alarms constantly. (See [03 — Latency Budgets](../latency-and-throughput/senior.md) on the p99 trap.)
  - Load shape, warm-up (caches, connection pools, JIT), and coordinated omission in the load generator all bias the result if mishandled.

Practical consequences: gate microbenchmarks tightly with full statistical machinery, but treat them as *early-warning of a component*, not proof of system impact. Gate macro tests on robust central metrics (throughput, p50) with wider tolerances and longer baselines; treat their p99 as a trend signal, not a hard gate. **The two are complementary**: micro catches the regression early and points at the function; macro confirms it actually moves the system metric users feel. A micro regression that doesn't show up in macro is often correctly ignored.

---

## Storing History for Trend Analysis

Change-point detection, calibration from the noise floor, and trend alarms all require one thing the naive "compare two runs" model doesn't: **durable, queryable history of every benchmark result.** This is infrastructure, and it's worth designing deliberately.

Store, per result, enough to reconstruct *and trust* the number later:

- **Identity:** commit SHA, branch, benchmark name, metric name (time/op, allocs/op, throughput, p99).
- **Value + dispersion:** the central estimate *and* its variance/CV/sample count — a point without its dispersion can't be statistically compared later.
- **Environment fingerprint:** runner hostname/class, CPU model, kernel, toolchain version, governor/turbo state, key benchmark flags. This is what lets you *exclude* cross-host comparisons and detect environment-driven shifts (a runner upgrade that moves every number). Without it, a fleet change looks like a code regression in every benchmark at once.
- **Timestamp and build metadata** for correlating with infra events.

A time-series database (or even a columnar table) keyed on `(benchmark, metric, commit_time)` is the natural shape; it makes "give me the last 90 days of `BenchmarkEncode` time/op on bare-metal-runner-class-A" a single query — exactly the input E-divisive and CUSUM consume. Go's own **perf dashboard** (`perf.golang.org`, backed by the `golang.org/x/perf` tooling and `benchfmt` format) is a clean reference: it ingests `benchstat`-format results keyed by commit, stores them, and renders per-benchmark history so a maintainer can eyeball the change point and click through to the commit. The storage *is* the product — detection is just a query over it.

---

## A Tour of Real Systems

The patterns above aren't theoretical; they're reverse-engineered from systems that run this at scale.

- **Chromium perf bots / Pinpoint.** Chromium runs thousands of benchmarks across a fleet of dedicated, hardware-pinned bots (real Android phones in racks, dedicated desktops — never shared cloud). Regressions are detected over the *time series* (anomaly/change-point detection on the dashboard, `chromeperf`), then **Pinpoint** automatically bisects the culprit commit by re-running the benchmark across the range on matching hardware, and files a bug with the offending CL. It's the canonical "change-point detection + automated same-hardware bisection" pipeline, and the dedicated-hardware insistence is the load-bearing part.
- **MongoDB DSI + Hunter / E-divisive.** MongoDB's Distributed Systems Infrastructure (DSI) runs macro/load performance tests on controlled, provisioned hardware; the signal-processing layer applies **E-divisive means** change-point detection over each metric's history to find statistically justified level shifts, then triages and bisects. Their open-sourced **Hunter** tool packages the change-point detection for anyone's CSV/time-series data. This is the production reference for "don't do pairwise, do change-point on the series."
- **Go's `benchstat` + perf dashboard.** The microbenchmark reference: `benchstat` does the Mann-Whitney U comparison with effect size for local A/B, and `perf.golang.org` stores history per commit for trend viewing. Simple, statistically honest, and widely copied.
- **JMH (Java).** Not a regression *system* but the gold-standard *measurement* layer: forks the JVM to defork JIT state, warms up, runs measurement iterations, and reports score with confidence intervals — the trustworthy per-build samples you then feed into your own comparison and storage.

The throughline across all four: **dedicated/controlled hardware, distribution-based statistics, change-point detection over stored history, and automated bisection to the commit.** Every robust system converges on the same four pillars.

---

## Common Mistakes

1. **Comparing single runs (`n = 1`).** One number per side gives the test no way to estimate variance — `benchstat` can't run Mann-Whitney, and any threshold you apply is a coin flip. Always collect many runs per side (≥6–10) before comparing.
2. **Using a t-test (or comparing means) on latency.** Latency is right-skewed with a heavy tail; the mean is dragged by outliers and the normality assumption is false. Use Mann-Whitney U / Wilcoxon on ranks.
3. **Gating on p-value alone.** With enough samples a 0.2% shift is "significant" and floods you with non-regressions. Require an effect-size floor *and* significance.
4. **Ignoring multiple comparisons.** Running hundreds of benchmarks at α = 0.05 guarantees a daily flood of false positives. Apply Bonferroni (small set) or Benjamini-Hochberg FDR (large suite).
5. **Pairwise comparison against the previous commit on `main`.** It fires on environment drift and run-to-run noise while missing slow accumulating slopes. Use change-point detection over the stored series.
6. **Microbenchmarking on shared cloud CI and trusting the absolute numbers.** 10–30% variance makes real 3–8% regressions undetectable. Get bare-metal pinned runners, or compare baseline-vs-candidate *alternated on the same host in one job* so noise is common-mode.
7. **Picking the threshold by taste instead of measuring the noise floor.** "Fail on +5%" is too strict for noisy benchmarks and too loose for quiet ones. Run the same commit 30× to measure each benchmark's real noise, then set per-benchmark thresholds above it.
8. **A flaky predicate inside `git bisect run`.** Bisection has no error correction — one mislabeled commit sends it down the wrong half permanently. Make the predicate statistically robust (many samples, stable host) and use `exit 125` to skip unbuildable commits.

---

## Apply it

1. State the system invariant that **Performance Budgets and Regression Testing** must protect.
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

- Which invariant must remain true when Performance Budgets and Regression Testing fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
- You have 500 benchmarks running on every PR — what statistical problem does that create, and how do you handle it?
- Pairwise A/B (PR vs baseline) is the obvious gate — what does it miss, and what's the alternative?
- What makes a good baseline to compare against, and why is "the previous run" a bad one?
- Why do microbenchmark gates break on standard cloud CI runners, and how do you get stable measurements despite that?
- CI reports a 4% regression on a hot path — walk through how you'd decide whether it's real or noise.
- A real regression shipped to production despite a green perf gate — how would you root-cause the gate's failure?
