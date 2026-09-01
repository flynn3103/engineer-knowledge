# Benchmarking and Microbenchmarks — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Benchmarking and Microbenchmarks** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Performance](../README.md) → Benchmarking and Microbenchmarks
> *The senior page taught you to write a microbenchmark that doesn't lie to itself — defeating dead-code elimination, warming the JIT, reporting a distribution instead of a mean. This page is about benchmarking as infrastructure: a stable harness other people trust, a dedicated runner that isn't a noisy cloud VM, a pipeline that catches a 3% regression before it ships, and the judgment to know when a green microbenchmark is still lying about production.*

---

## A Benchmark Harness Is Infrastructure, Not a Script

The moment more than one person relies on a benchmark number, the benchmark stops being a script and becomes infrastructure — with the same obligations as any shared system:

- Stable inputs.
- Versioned configuration.
- Reproducible output.
- A contract about what the number means.

A harness that people trust has these properties:

- **Pinned environment.** Same compiler/JIT, same CPU governor, same allocator, same dependency versions. A benchmark whose result depends on whoever's laptop ran it is worse than no benchmark — it manufactures false signal. Pin the toolchain the same way you pin a [build toolchain](../../../Craftsmanship/build-source-code/01-build-fundamentals/professional.md).
- **Fixed, versioned workload.** The input data is part of the benchmark. If the corpus changes, the number changes, and a "regression" is really a workload change. Store the corpus with a hash; record the hash in the result.
- **Self-describing output.** Every result carries the commit SHA, host ID, toolchain version, workload hash, and the raw sample distribution — not just a mean. A number without provenance can't be compared across time.
- **Deterministic invocation.** One command, no manual steps. `make bench` or `cargo bench` or a single CI job. If running the suite requires a wiki page of steps, it will be run wrong.

A minimal harness contract, encoded as the shape of every result record:

```json
{
  "benchmark": "json/encode/large-struct",
  "commit": "a1b2c3d",
  "host_id": "bench-runner-01",
  "toolchain": "go1.22.3",
  "workload_hash": "sha256:9f2a…",
  "samples_ns": [1182, 1175, 1190, 1183, 1179, 1201, 1176],
  "iterations": 50000,
  "allocs_per_op": 3,
  "bytes_per_op": 256,
  "started_at": "2026-06-19T14:02:11Z"
}
```

Notice what is *not* here: a single "result" field.

- The harness emits the raw distribution and lets the comparison layer ([regression detection](../performance-budgets-and-regression-testing/professional.md)) decide whether two distributions differ.
- The harness measures; it does not judge.
- Keeping those concerns separate is what lets you change the statistical test later without re-running history.

> **The professional reality:** the hardest part of a benchmark harness is not the measurement loop — `testing.B`, JMH, and Criterion already solve that. It's making the result *comparable across machines and across months*. That means provenance on every sample and a workload that is versioned, not ambient. Treat the harness like a measurement instrument: it needs calibration, a serial number, and a logbook.

---

## The Runner Problem — Why Cloud CI Makes Microbenchmarks Worthless

This is the single most important professional insight on this page: **a shared cloud CI runner cannot produce a trustworthy absolute microbenchmark number, and most teams don't realize it until they've shipped a regression a noisy benchmark failed to catch.**

- A microbenchmark measures nanoseconds-to-microseconds per operation. To resolve a 3% change, your measurement noise must be well under 3%.
- A standard GitHub Actions / GitLab SaaS / generic cloud CI runner gives you noise far larger than that, because:

- **Noisy neighbors.** You're on a shared hypervisor. Another tenant's workload steals CPU, thrashes the shared L3 cache, and saturates memory bandwidth — invisibly. The same code can run 30%+ slower depending on who else landed on the box.
- **CPU frequency is not yours to control.** Turbo boost, thermal throttling, and cloud-vendor frequency scaling move the clock under you. You can't pin the governor to `performance` on a runner you don't own.
- **vCPUs are shared cores.** Hyperthread siblings and burstable instance credits (AWS `t3`, etc.) mean your "CPU" is a time-slice, not a core. Burstable instances literally throttle after you exhaust credits — mid-suite.
- **Ephemeral, heterogeneous hardware.** Today's runner is a Skylake, tomorrow's is an Ice Lake or Graviton. Absolute numbers across runs compare different silicon.

The result: variance of 20–50% run-to-run, which drowns every real regression smaller than "we accidentally added an N² loop."

- Teams that benchmark on cloud CI get a check that is *red for noise and green for noise*, learn it's untrustworthy, and route around it.
- A benchmark people ignore is negative value — it cost CI minutes and trained the team to dismiss perf signal.

**What to do instead — in priority order:**

1. **Relative comparison on the same host, same run (A/B in one job).** The highest-leverage technique. Don't compare today's runner to last week's runner. In a *single* CI job on *one* machine, check out `main`, build and benchmark it; check out the PR, build and benchmark it; compare the two distributions *to each other*. The noisy neighbor and the frequency drift affect both arms roughly equally and cancel out. This works even on a cloud VM, because you've turned an absolute measurement into a relative one. This is the technique that makes cloud benchmarking salvageable.

   ```bash
   # A/B in one job: both arms on the same host, interleaved
   git checkout main      && go test -bench=. -count=10 ./... > base.txt
   git checkout $PR_SHA   && go test -bench=. -count=10 ./... > new.txt
   benchstat base.txt new.txt        # reports delta + p-value, not absolutes
   # Interleaving (alternating base/new runs) further cancels slow drift.
   ```

2. **A dedicated bare-metal benchmark runner.** For absolute numbers and the smallest detectable regression, you need a machine you control: bare metal (not a VM), CPU governor pinned to `performance`, turbo/boost disabled, hyperthreading off, the process pinned to an isolated core (`isolcpus` + `taskset`/`cset`), ASLR and address-space randomization understood, swap off, and nothing else scheduled. Such a box drives run-to-run noise under 1–2%, enough to resolve a 3% regression reliably. One dedicated machine (even a refurbished workstation) serving the whole org is cheap relative to the value of a trustworthy perf gate.

   ```bash
   # Bare-metal runner setup (Linux), per boot / per run
   sudo cpupower frequency-set -g performance        # no frequency scaling
   echo 0 | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/boost   # no turbo jitter
   echo off | sudo tee /sys/devices/system/cpu/smt/control        # no hyperthreading
   # kernel cmdline: isolcpus=2,3 nohz_full=2,3 rcu_nocbs=2,3
   taskset -c 2 ./bench_runner                         # pin to the isolated core
   ```

3. **Accept that cloud absolute numbers are directional only.** If you can't get bare metal and can't do A/B-in-one-run, treat cloud microbenchmark absolutes as a smoke test for catastrophic regressions (2x+) only, and do real perf validation on a controlled host before release. Don't pretend a 5% cloud delta is signal.

> **The hard rule:** *never gate on absolute microbenchmark numbers measured on shared cloud CI.* Either compare two builds on the same host in the same run (relative, drift cancels), or measure on a dedicated bare-metal runner (absolute, noise controlled). A benchmark whose variance exceeds the regression you care about is not a weak signal — it's an anti-signal that trains people to ignore performance.

---

## Continuous Benchmarking Pipelines and Dashboards

Once you have a trustworthy harness and a runner, the goal is to make performance a *continuous, visible* property — like test coverage or build status — rather than something measured in a panic after an incident.

The pipeline shape:

```
PR opened ──► CI: A/B benchmark on same host (fast, relative gate)
                   │
                   ├─ regression > threshold? ─► block + comment with benchstat table
                   └─ ok ─► merge

merge to main ──► dedicated bare-metal runner (nightly or per-merge)
                   │   absolute numbers, full suite
                   ├─ store result (commit, host, distribution)
                   ├─ compare to rolling baseline ─► alert on regression
                   └─ push to dashboard (trend over time)
```

Two distinct stages, because they answer different questions:

- **The PR gate (relative, fast).** Runs the *affected* benchmarks A/B on one host, in minutes, and posts a comment. Its job is to stop an obvious regression from merging. It tolerates cloud noise because it's relative. Keep it fast or people will route around it.
- **The trend pipeline (absolute, thorough).** Runs the full suite on the dedicated runner per-merge or nightly, stores every result, and feeds a dashboard. Its job is to catch slow drift — the 0.5%-per-week creep that no single PR trips but that adds up to 30% over two quarters.

A practical PR-gate job that comments on regressions:

```yaml
# .github/workflows/bench.yml (relative A/B gate)
bench:
  runs-on: [self-hosted, bench]      # ideally your controlled runner; cloud works for relative
  steps:
    - uses: actions/checkout@v4
      with: { fetch-depth: 0 }
    - run: |
        git checkout ${{ github.base_ref }}
        go test -bench=. -benchmem -count=8 ./pkg/hotpath > base.txt
        git checkout ${{ github.sha }}
        go test -bench=. -benchmem -count=8 ./pkg/hotpath > new.txt
        benchstat -format csv base.txt new.txt > delta.csv
    - run: ./scripts/comment_if_regression.sh delta.csv 3.0   # fail if >3% slower, p<0.05
```

The alerting logic — *is this delta a real regression or noise?* — is non-trivial and belongs to [regression detection](../performance-budgets-and-regression-testing/professional.md):

- A Mann-Whitney U test on the two sample distributions.
- A minimum effect size (don't alert on a statistically-significant 0.3% that no one cares about).
- A guard against alerting on a single bad run.

The benchmarking layer's job is to *produce clean distributions*; the regression layer's job is to *decide if they differ*. Don't conflate them.

The dashboard makes the trend pipeline pay off.

- A per-benchmark time series (latency/op on Y, commit/date on X) annotated with merge SHAs turns "perf got worse sometime this quarter" into "perf stepped 9% at commit `e4f7a1` on May 3."
- Grafana over a results table, or a hosted tool (Bencher, `cargo-criterion` + a viewer, the Go `benchmark` dashboards), both work.
- The non-negotiable is *annotation by commit* — a trend line without commit markers tells you something is wrong but not where.

> **The professional reality:** a continuous benchmarking pipeline is two pipelines with different SLAs — a fast relative gate that blocks PRs, and a thorough absolute trend job that catches drift. Conflating them gives you a gate too slow to keep and a trend too noisy to read. And the dashboard is only useful if every point links back to a commit.

---

## Result Storage, Baselines, and Trend Tracking

Benchmark results are time-series data with provenance, and the cheapest correct storage is usually a structured append-only store keyed by `(benchmark, commit, host)`.

The schema matters more than the technology — Postgres, a columnar store, or even committed JSON files in a results repo all work if the record carries enough context.

What every stored record needs (so a future comparison is valid):

```json
{
  "benchmark": "serialize/order-batch",
  "commit": "e4f7a1c", "parent": "d9c0b2a",
  "host_id": "bench-runner-01", "toolchain": "rustc-1.78.0",
  "workload_hash": "sha256:1c7e…",
  "metric": "ns_per_op",
  "p50": 842, "p90": 871, "p99": 940,
  "raw_samples": [/* … for re-running the stat test later */],
  "git_branch": "main", "ts": "2026-06-19T03:11:00Z"
}
```

**Baselines** are the comparison target, and choosing the baseline is a design decision:

- **Parent-commit baseline (relative gate).** Compare a commit to its parent. Best for catching a single regressing change. This is what the A/B PR gate does.
- **Rolling-window baseline (trend).** Compare to the median of the last N green runs on the same host. Robust to single-run noise; catches slow drift. A regression alert fires when the new distribution is significantly worse than the rolling baseline by more than the minimum effect size.
- **Release baseline (product SLA).** Compare to the last released version. This is the number you cite to product: "v2.4 encodes order batches 11% faster than v2.3." It's a [performance budget](../performance-budgets-and-regression-testing/professional.md) anchor.

Baseline hygiene that bites people:

- **Re-baseline only on the same host.** A baseline measured on `runner-01` is meaningless for a result from `runner-02`. Key baselines by host.
- **Re-baseline after intended changes.** When you deliberately accept a 5% slowdown for a feature, *move the baseline* and note why, or every future run alerts forever.
- **Keep raw samples, not just summaries.** If you only store the mean, you can never re-run a better statistical test later or investigate whether a "regression" was bimodal (a GC-pause tail) vs a true shift.

> **The principle:** a benchmark result is only meaningful relative to a baseline measured under the same conditions. Store provenance and raw samples so comparisons stay valid as your tooling evolves, key baselines by host, and treat a deliberate slowdown as a baseline *move*, not a standing alert. A stale baseline produces alert fatigue, and alert fatigue kills the whole pipeline's credibility.

---

## When a Microbenchmark Is a Lie About Production

A microbenchmark can be *internally honest* — DCE-defeated, warmed up, low variance, statistically sound — and still tell you something false about production.

This is the most expensive class of benchmarking error because the number *looks* trustworthy. The mechanisms:

- **Cache warm vs cold.** A microbenchmark hammers the same small working set in a tight loop, so by the second iteration everything is in L1/L2 and the branch predictor is trained. Production touches that code path once per request, cold, with the caches full of *other* requests' data. A function that's 50ns hot can be 400ns cold. Your benchmark measured the warm case; production lives in the cold case.
- **Single-tenant vs contended.** The benchmark runs alone on the box. Production runs that code on 64 threads contending for the same lock, the same allocator arena, the same cache lines (false sharing). A lock-free path that benchmarks beautifully single-threaded can collapse under contention — see [concurrency overhead](../concurrency-and-contention/README.md). The microbenchmark measured zero contention; production has plenty.
- **Synthetic vs real data distributions.** Benchmarks use clean, uniform, or worst-case-free inputs. Production data is skewed: 90% of strings are short and one is 4 MB; the hash keys cluster; the JSON is mostly nulls. A parser benchmarked on uniform input can be 3x slower on the real long-tail distribution, or vice versa. *The input distribution is part of the measurement* — a benchmark on the wrong distribution measures the wrong thing.
- **Allocation amortized away.** Tight loops let the allocator and GC reach a steady state the benchmark doesn't pay for; production's bursty allocation triggers GC pauses the microbenchmark never sees. Always report `allocs/op` and validate against production GC behavior.
- **The whole-system effect is missing.** Making a function 2x faster that's 1% of request time is invisible in production (Amdahl). The microbenchmark celebrates a real local win that the macro picture renders irrelevant.

The defense is layering, not abandoning microbenchmarks:

1. **Microbenchmark** to iterate fast on a hot function (cheap, fast feedback).
2. **Validate against a macrobenchmark / load test** with realistic concurrency and data before believing the win is real (see [throughput vs latency](../latency-and-throughput/README.md)).
3. **Confirm in production** with a canary and real metrics. The only authority on production performance is production.

> **The hard-won lesson:** an internally-honest microbenchmark answers "is this function faster in isolation?" — which is a *different question* from "is the system faster for users?" The gap is cache state, contention, data distribution, and Amdahl. Treat a microbenchmark win as a hypothesis to be confirmed by a load test and a canary, never as a conclusion. The number being low-variance does not make it relevant.

---

## Flame-Graph-Guided Benchmark Targeting

The complement to "don't trust every benchmark" is "don't *write* benchmarks blindly."

- The most common waste in benchmarking is optimizing — and benchmarking — code that doesn't matter.
- The flame graph tells you where the time actually goes, and that's where your benchmarks (and optimization effort) belong.

The disciplined loop:

1. **Profile the real workload first** ([01 — Profiling](../profiling/README.md)). A CPU flame graph from a production-like load shows the widest frames — the functions that own the most wall-clock or CPU time.
2. **Write microbenchmarks for the wide frames, not the narrow ones.** If `json.Marshal` is 22% of CPU and your custom `validate()` is 0.4%, benchmark the marshaling path. Benchmarking `validate()` is effort spent on a frame too thin to matter.
3. **Use the flame graph to scope the benchmark correctly.** The graph shows whether the cost is in *your* code or in a framework/library frame underneath it — which directly determines whether your benchmark should isolate your code or include the framework. (This is exactly the trap in the war story below.)
4. **Re-profile after optimizing** to confirm the wide frame shrank and a new bottleneck didn't just take its place.

This turns benchmarking from a guessing game into targeted work:

- You benchmark the hot 5% of code that owns 80% of the time.
- You ignore the cold 95% — because a benchmark of cold code is, by construction, measuring something that can't move the system.

> **The principle:** a flame graph is the map; benchmarks are the measurements you take at the marked locations. Writing a benchmark without first profiling is surveying random coordinates. Benchmark the widest frames; ignore the thin ones — Amdahl guarantees the thin ones can't matter.

---

## The Cost and ROI of Benchmarking

Benchmarks are not free.

- Each one costs authoring time, CI minutes, runner wear, and maintenance as the code evolves.
- Most insidiously, each one costs *attention*: a 40-minute suite with 300 benchmarks is a suite no one reads.
- The professional question is not "should we benchmark?" but "*which* code earns a benchmark?"

Benchmark when the ROI is clear:

- **Hot paths** the flame graph proves own real time. A 5% win here is worth real money in fleet CPU and latency.
- **Regression-prone code** — the serializer, the core data structure, the request router, the hot allocation path — code where a careless change silently costs 10% and no test would catch it. These earn a *gate*, not just a benchmark.
- **Code with a contractual performance SLA** — a library others depend on for speed, a latency-budgeted component.
- **Algorithmic decisions** where you're choosing between implementations and need a defensible comparison.

Do *not* benchmark:

- **Cold code** — startup paths, config parsing, admin endpoints. A microsecond saved on something that runs once at boot is zero value.
- **Code that's about to change** — benchmarking churning code is maintaining benchmarks faster than they pay back.
- **Everything, reflexively.** "100% benchmark coverage" is an anti-goal. It produces a slow suite of mostly-noise that buries the few benchmarks that matter and trains the team to ignore the whole thing.

A simple ROI heuristic: a benchmark is worth maintaining if `(probability the code regresses) × (cost of a missed regression) > (authoring + CI + maintenance cost)`. For the request hot path that's clearly true; for a config parser it's clearly false. Spend your benchmarking budget where the flame graph and the regression history say it pays.

> **The professional reality:** the goal is not maximum benchmark coverage — it's maximum *signal per minute of suite time and per unit of attention*. Benchmark the hot, regression-prone, SLA-bound code and gate it; skip the cold and the churning. A small suite people trust and run beats a huge suite people ignore, every time.

---

## Decision Frameworks

**Where do I run this benchmark? Ask:**
- Do I need an *absolute* number (latency/op, throughput)? → dedicated bare-metal runner, governor pinned, isolated core. Cloud absolutes are noise.
- Do I just need "is the PR faster or slower than main?" → A/B in one CI job on the same host; relative, drift cancels; cloud is fine.
- Can I get neither? → treat cloud absolutes as a catastrophic-regression smoke test only (2x+), and validate on a controlled host before release.

**Should this code have a benchmark at all? Ask:**
- Does the flame graph show it owning real time? → yes, benchmark it.
- Is it regression-prone (serializer, core data structure, hot path)? → yes, and *gate* it.
- Is it cold (startup, config, admin) or about to be rewritten? → no.
- Am I chasing "100% benchmark coverage"? → stop; that's an anti-goal.

**Do I believe this microbenchmark's win? Ask:**
- Was the input the real production distribution, or synthetic/uniform? → if synthetic, distrust.
- Warm cache + single-tenant in the bench vs cold + contended in prod? → if so, validate with a load test.
- Is the function a meaningful fraction of request time (flame graph)? → if <1–2%, Amdahl says it won't move the system.
- Confirmed by a macrobenchmark and a canary? → if not, it's a hypothesis, not a result.

**What's my pipeline shape? Default to:**
- Fast *relative* A/B gate on PRs (blocks obvious regressions) + thorough *absolute* trend run on a dedicated host (catches creep), with a commit-annotated dashboard and the stat test owned by [regression detection](../performance-budgets-and-regression-testing/professional.md).

---

## Common Mistakes

1. **Gating on absolute microbenchmark numbers from shared cloud CI.** Variance (20–50%) dwarfs real regressions; the check goes red/green at random and the team learns to ignore it. Use A/B-in-one-run relative comparison, or a dedicated bare-metal runner for absolutes.

2. **No provenance on results.** A number without commit SHA, host ID, toolchain version, and workload hash can't be compared across time or machines. Every sample carries its context, or it's not infrastructure.

3. **Believing a low-variance microbenchmark is therefore relevant.** Stable ≠ representative. Warm-cache, single-tenant, synthetic-input numbers routinely disagree with production. Validate wins with a load test and a canary.

4. **Benchmarking the framework instead of the code.** If the benchmark routes through middleware/reflection/ORM, most of the measured time isn't your change. Flame-graph your own benchmark; isolate the code under change.

5. **Benchmarking everything for "coverage."** A 40-minute suite of mostly cold-code noise buries the few benchmarks that matter and trains people to skip the whole thing. Benchmark hot, regression-prone, SLA-bound code only.

6. **Only a per-PR gate, no trend pipeline.** Catches steps, misses the 0.5%-per-week creep that compounds to 30%. You need the absolute trend run with a commit-annotated dashboard too.

7. **Stale baselines.** A deliberate slowdown not re-baselined alerts forever; a baseline from a different host is meaningless. Key baselines by host; move them on intended changes; keep raw samples to re-test later.

8. **Conflating "measure" with "judge."** The harness should emit distributions; whether two distributions differ belongs to [regression detection](../performance-budgets-and-regression-testing/professional.md). Mixing them locks you into one stat test and one threshold forever.

---

## Apply it

1. Define the user or business outcome that **Benchmarking and Microbenchmarks** should improve.
2. Assign one owner for code, contracts, operations, and incidents.
3. Split delivery into reversible increments that produce evidence early.
4. Publish responsibilities, escalation paths, and compatibility windows.
5. Stop or expand only when the agreed measures support that decision.

## Verify your work

- Each increment has an owner, rollback path, and observable exit condition.
- Adoption, reliability, delivery time, and coordination cost are measured.
- Incident and migration exercises prove that responsibility is executable.
- The old path is removed only after telemetry proves it is unused.

## Review questions

- Which measurable outcome justifies investing in Benchmarking and Microbenchmarks?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
- You're setting up benchmarking for a new library — what do you benchmark, and what do you deliberately skip?
- How do you keep benchmarks useful in CI without them becoming flaky, ignored gates?
- When should you decide not to benchmark at all, and just ship?
- A teammate's PR claims a 15% speedup backed by a microbenchmark — what do you check before approving?
- Why can't a shared cloud CI runner produce a trustworthy absolute microbenchmark number, and what do you do instead?
- How do you decide what belongs in a fast per-PR benchmark gate versus a slower trend-tracking pipeline?
