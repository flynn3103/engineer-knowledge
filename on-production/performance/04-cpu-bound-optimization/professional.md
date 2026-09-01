# CPU-Bound Optimization — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **CPU-Bound Optimization** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Performance](../README.md) → CPU-Bound Optimization
> *The senior page taught you to find and fix the hot path. This page is about deciding whether you should — when a 5% CPU win pays an engineer's salary and when it's a vanity metric, how to feed production profiles back into your compiler, and how to drop to a Rust kernel without your on-call rotation paying for it later. CPU here stops being a flame graph and becomes a line on a cloud bill.*

---

## The ROI of CPU Work — Cycles as Dollars

Before any CPU optimization, do the arithmetic. The unit that matters is **cost saved per engineer-time spent**, and it's almost always estimable to within a factor of two before you write a line of code.

- Take the service's steady-state core count (from your autoscaler or capacity dashboard).
- Multiply by the effective per-core-hour cost (on-demand list price is the ceiling; with reserved/spot/committed-use discounts the *effective* rate is often $0.01–0.02/core-hour) → annual compute cost.
- A CPU reduction that lets the autoscaler hold the same SLO with fewer cores converts directly into that percentage of the bill — **but only if the service is actually CPU-bound at its scaling boundary.** If your autoscaler scales on memory, connection count, or a fixed replica floor, a CPU win buys you nothing on the bill; it buys headroom, which has value but is not cash.

```
Annual compute  = cores × $/core-hour × 8760
                = 4000 × $0.03 × 8760  ≈ $1,050,000
5% CPU win      ≈ $52,500/yr  (recurring)  → pays a sprint in one quarter
5% on an $8K/yr service ≈ $400/yr          → an engineer-month loses ~$15K net
```

Three refinements separate the professional estimate from the napkin one:

- **Does the win remove capacity, or just headroom?** Only wins that the autoscaler can act on (CPU is the binding constraint) become dollars. Confirm what your HPA / scaling policy actually keys on.
- **Is the win at the scaling boundary or in the noise?** A 30% speedup in a function that's 2% of total CPU is a 0.6% service win. Amdahl governs the bill exactly as it governs latency — optimize what dominates the *aggregate* profile, not what's locally ugliest.
- **Does the win persist?** A one-time win that regresses in three releases (no [regression gate](../07-performance-budgets-and-regression-testing/professional.md)) is a depreciating asset. A 5% win protected by a CI benchmark gate is the one that actually pays the salary year after year.

> **The professional framing:** "premature optimization" isn't about *when in the code's life* you optimize — it's about *optimizing before you've shown the work has positive ROI.* The senior who hand-tunes a SIMD loop on a service that costs $5K/year hasn't been clever; they've spent a $15K engineer-month to save $250. Do the multiplication first. It takes five minutes and it's the highest-leverage thing on this page.

---

## Optimization Altitude — Start at the Top

CPU wins live at four altitudes, and the cost-to-benefit ratio is brutally non-linear across them. You almost always start at the top and descend only when forced.

| Altitude | Example | Typical win | Maintainability cost |
|---|---|---|---|
| **Algorithm / complexity** | O(n²) → O(n log n); cache a recomputed result; batch N calls into 1 | 10×–1000× | Often *lowers* it (less code) |
| **Data structure** | `map` → slice + binary search; B-tree → hash; pointer-chasing → flat array | 2×–10× | Neutral to slightly higher |
| **Memory layout** | AoS → SoA; pad to avoid [false sharing](../06-concurrency-and-contention/professional.md); arena allocation | 1.2×–3× | Higher — reads less obviously |
| **Micro-architecture** | SIMD intrinsics, branch elimination, manual loop unrolling, prefetch hints | 1.1×–2× | Much higher — and fragile across CPUs |

The reason to start high: the top of this table dominates the bottom *and* costs less to maintain. An O(n²)→O(n log n) change at n=10⁴ is a 700× algorithmic win; the best hand-vectorized inner loop will get you maybe 4×. If you vectorize first, you've spent your hardest engineering on the quadratic loop — and the moment someone fixes the algorithm, your SIMD code is deleted, having earned nothing.

The discipline:

- **Profile the aggregate, then ask "why is this hot at all?" before "how do I make this instruction faster?"** Frequently the hot function shouldn't be called as often as it is — a caching or batching change at a higher altitude deletes the hotspot entirely.
- **Exhaust each altitude before descending.** Only reach for memory layout once the algorithm and data structures are right; only reach for intrinsics once layout is right. Each step down roughly doubles maintenance cost for a fraction of the win.
- **Let the compiler own the bottom altitude where it can.** Auto-vectorization, inlining, and PGO (next section) cover much of the micro-arch altitude *for free and portably*. Hand-written intrinsics are the last resort, justified only when the compiler provably can't and the kernel is hot enough to matter.

> **The trap, named:** "micro-optimization theater" is descending to the bottom altitude because it *feels* like hardcore performance work, while an algorithmic fix two altitudes up sits ignored. The flame graph tells you *where* the time goes; it does not tell you *which altitude* to fix it at. That judgment is yours, and it's where most CPU effort is wasted.

---

## Profile-Guided Optimization in a Production Pipeline

PGO (also AutoFDO / feedback-directed optimization) is the highest-leverage CPU lever most teams never turn on. The idea: a compiler optimizing blind has to *guess* which branches are taken, which functions are hot, and what to inline. Feed it a **profile of real execution** and it stops guessing — it lays out hot code contiguously, inlines along hot paths, and arranges branches so the common case falls through. Typical wins are **5–15% CPU, fleet-wide, for near-zero ongoing engineering cost.** That is often the single largest line-item-to-effort ratio available.

The production pattern is a closed loop: **collect profiles from prod → store them → feed them into the build.**

**Go (since 1.21)** makes this almost trivial — a `default.pgo` next to `main` is picked up automatically:

```bash
# 1. Collect a representative CPU profile from production (e.g. via pprof endpoint)
curl -o cpu.pprof "http://prod-host:6060/debug/pprof/profile?seconds=60"

# 2. Commit it as default.pgo (or wire it into the build); go build finds it automatically
cp cpu.pprof ./cmd/server/default.pgo
go build ./cmd/server      # PGO-optimized, no flags needed

# 3. Verify the win against the non-PGO baseline
benchstat baseline.txt pgo.txt   # expect ~2-14% on hot paths
```

**LLVM (C/C++/Rust) AutoFDO + BOLT** is the heavier-duty version that Google, Meta, and others run at scale:

```bash
# AutoFDO: collect with perf (LBR), convert to LLVM profile, rebuild
perf record -e cycles:u -j any,u -- ./server --bench   # sample with branch stacks
create_llvm_prof --binary=./server --out=app.afdo --profile=perf.data
clang -O2 -fprofile-sample-use=app.afdo -o server app.c

# BOLT: a post-link optimizer — re-orders the *already-linked* binary using the same profile
perf2bolt -p perf.data -o app.fdata ./server
llvm-bolt ./server -o server.bolt -data=app.fdata \
  -reorder-blocks=ext-tsp -reorder-functions=hfsort -split-functions
```

The professional concerns are operational, not theoretical:

- **Profile freshness and representativeness.** A profile from last quarter's traffic mix, or from a synthetic load test that doesn't match prod, can *mis*-optimize — laying out the wrong paths as hot. Refresh profiles on a cadence (e.g., weekly, sampled across the fleet and time-of-day), and treat the profile as a versioned build input like any other.
- **Build determinism.** A profile makes the build a function of *that profile*. Pin it, store it in artifact storage, and record which profile produced which binary, so a build is reproducible and a regression is bisectable. This is the same hermeticity discipline as toolchain pinning.
- **Stale-profile safety.** Both Go and LLVM tolerate a profile that no longer matches the source (a renamed function just doesn't get its hint) — it degrades to "no worse than non-PGO," it doesn't break. But a *systematically* stale profile silently caps your wins; monitor the realized delta.
- **Sampling overhead in prod.** Continuous profilers (Google Cloud Profiler, Parca, Pyroscope, Polar Signals) sample at well under 1% overhead, which makes "collect from prod" a standing service rather than a manual `curl`. That is the mature shape: profiling is always-on, profiles flow into the build automatically, and the feedback loop closes without a human in it.

> **Why this is the first thing to try:** PGO is a *coupon for free CPU*. Before anyone hand-optimizes anything, turn on PGO and re-measure — it's hours of work for a fleet-wide percentage win, it's portable, and it's maintenance-free. Hand-tuning a function that PGO would have improved anyway is wasted effort.

---

## Language and Runtime Choice as a CPU Lever

The coarsest CPU lever is the one you usually can't pull (the code's already written) but must understand — because it sets the ceiling everything else operates under, and because it's the right lever for *new* hot services.

The dominant runtime factors:

- **GC overhead and pauses.** A garbage-collected runtime spends CPU on the collector and, more subtly, on allocation and write barriers in the mutator. Go's GC is low-pause but you pay it in throughput and allocation cost; the JVM's collectors (G1, ZGC, Shenandoah) are tunable and can be excellent, but defaults rarely fit a latency-critical service. For an allocation-heavy hot path, **GC and allocator cost can be 20–40% of total CPU** — which is why the highest-altitude memory fix is often "stop allocating," not "tune the GC."
- **Escape analysis quality.** Whether a value lands on the stack (free) or the heap (allocation + GC pressure) is decided by the compiler's escape analysis. Go's is decent but conservative; the JVM's JIT does aggressive escape analysis and scalar replacement *at runtime* once a method is hot. This is why a Java microbenchmark can beat the equivalent Go one after warm-up — the JIT eliminated allocations Go's static analysis couldn't prove safe.
- **JIT vs AOT.** A JIT (HotSpot, V8) profiles at runtime and re-optimizes hot methods with knowledge a static compiler lacks — at the cost of warm-up time and memory, and unpredictability (de-optimization stalls). AOT (Go, Rust, C++, GraalVM native-image) gives instant peak performance and predictable behavior, no warm-up, lower memory — at the cost of the runtime adaptivity. For a long-running throughput service, the JIT's warm-up amortizes to nothing and its peak is hard to beat. For a short-lived process, a serverless cold-start, or a latency-SLO service that can't tolerate warm-up jitter, AOT wins decisively.
- **No-runtime languages.** Rust and C++ have no GC and no runtime tax — what you write is roughly what runs. That's the CPU ceiling, paid for in development cost and (for C++) memory-safety risk.

> **The decision, when you actually have it:** for a *new* service whose CPU cost will be a meaningful fleet line item, language choice is the cheapest 2–5× you'll ever get — far cheaper than clawing back the same factor in micro-optimization later. A latency-critical, allocation-heavy data plane is a strong case for Rust or carefully-tuned C++; a throughput service where developer velocity dominates is a strong case for Go or a well-tuned JVM. The mistake is treating language as fixed when you're greenfielding the very service whose CPU bill you'll be optimizing for the next three years.

---

## Compiler and Flag Governance

Optimization flags are a fleet-wide policy, not a per-developer preference, and the seductive ones have sharp edges.

**`-O2` vs `-O3`.** `-O2` is the production default for a reason: it's the well-tested, broadly-beneficial optimization set. `-O3` adds aggressive auto-vectorization and inlining that *sometimes* helps and *sometimes* hurts — more aggressive inlining can blow out the instruction cache, and the extra code size can make a hot loop slower, not faster. `-O3` is also less exercised, so it surfaces more compiler bugs and more undefined-behavior landmines in your own code. **Treat `-O3` as a per-target, benchmarked decision, never a blanket default.** Measure it on the actual binary; the win is frequently zero or negative.

**`-march=native` — the portability trap.** This tells the compiler to use every instruction the *build machine's* CPU supports — AVX-512, BMI2, whatever. It's a real win on a homogeneous fleet you fully control. It's a **production incident** the day a binary built on a new CI runner (AVX-512) lands on an older host (no AVX-512) and dies with `SIGILL — illegal instruction`. The professional move is to pin an explicit, fleet-wide baseline (`-march=x86-64-v2` or `-v3`, or an explicit `-mavx2`) that you *know* every target supports, never the build machine's incidental capabilities.

```bash
# DANGER: optimizes for the build box; SIGILLs on any older host
clang -O2 -march=native -o server app.c

# SAFE: explicit baseline every host in the fleet is guaranteed to support
clang -O2 -march=x86-64-v3 -o server app.c   # AVX2/BMI2 baseline, fleet-pinned

# Runtime dispatch: ship one binary, pick the best path per host
#   compile multiple versions of a hot kernel, choose at startup via CPUID
clang -O2 -mavx2 -DKERNEL_AVX2 ... ; clang -O2 -DKERNEL_SCALAR ...   # selected at runtime
```

**LTO (link-time optimization).** Cross-module inlining and dead-code elimination across the whole program — a real CPU and binary-size win, and it composes with PGO (PGO tells LTO *what* to inline). The cost is build time (full/monolithic LTO can be very slow; thin-LTO is the scalable middle ground) and harder debugging. **ThinLTO + PGO is the modern production combination** for C++/Rust release builds; reserve full LTO for the rare case where the extra cross-module work measurably pays.

> **The governance reality:** these flags belong in a shared, reviewed build template — never copy-pasted per-project where they drift, and never set to the build machine's capabilities. A security review or a postmortem will eventually ask "why did this binary SIGILL on 15% of the fleet?" and the answer should never be "someone left `-march=native` in a Makefile." Pin the baseline, benchmark `-O3`/LTO per target, and verify the emitted ISA in CI.

---

## Dropping to a Native Kernel — and Wrapping It Safely

Sometimes the algorithm is optimal, the layout is tuned, PGO is on, and the hot kernel is *still* the bottleneck — and the host language's runtime is the ceiling. That's when you drop one hot kernel to C, Rust, or hand-written assembly. The skill is not writing the kernel; it's **containing it** so its complexity and risk never leak into the rest of the codebase.

When it's justified:

- The kernel is a *measured* dominant fraction of CPU (Amdahl: a 10× win on 2% of CPU isn't worth a new language boundary).
- The work is tight, numeric, branch-light, or SIMD-friendly — exactly what a managed runtime is worst at and what intrinsics are best at.
- PGO and higher altitudes are exhausted; the remaining win provably requires instructions or memory control the host language won't emit.

How to wrap it safely:

- **Isolate it behind a stable, narrow interface.** One function, one well-documented contract (preconditions, alignment, length invariants), with a *pure-host-language reference implementation kept alongside it.* The reference is your correctness oracle and your fallback.
- **Differential-test the kernel against the reference** with property-based / fuzz inputs, on every CI run. A hand-written SIMD kernel that's right for the cases you thought of and wrong for the tail is the classic, dangerous bug.
- **Pay the FFI tax knowingly.** Crossing the Go cgo boundary or the JNI boundary has real per-call overhead (cgo is roughly tens of nanoseconds; JNI similar) and can pessimize the scheduler/GC (a cgo call occupies an OS thread). **Batch across the boundary** — call the kernel once per 10⁴ elements, not once per element — or the boundary cost eats the kernel win.
- **Contain the unsafety.** In Rust, the `unsafe` block is the box; keep it tiny, audited, and wrapped in a safe API. In C, the kernel is the one place memory-safety bugs can live, so it gets the heaviest review and the fuzzing. Document, at the call site, *why* this exists and what would let you delete it.

> **The maintainability contract:** a native kernel is a debt you take on deliberately and pay down in documentation and tests. The rest of the team should be able to use it through a safe, obvious interface without ever reading the intrinsics — and a future engineer should find a comment explaining the benchmark that justified it, the reference implementation that validates it, and the conditions under which it can be ripped out. A hot kernel without that scaffolding is a landmine, not an optimization.

---

## The Maintainability Cost of Fast Code

Every optimization below the algorithmic altitude trades readability for speed, and that trade is a real, recurring cost paid by everyone who touches the code afterward. The professional skill is making the trade *visibly* and *locally*.

- **Isolate hot kernels; keep the rest idiomatic.** The 3% of the code that's hot can afford to be ugly; the other 97% should stay readable. Don't let micro-optimizations metastasize across a codebase where they earn nothing — a manually-unrolled loop in a cold path is pure cost.
- **Document the "why," not the "what."** Optimized code is non-obvious by construction; the comment that matters explains *the measurement that justified it* ("benchmark: this AoS→SoA flip cut L2 misses 60%, 1.8× on the hot path — see bench/foo_test.go") so the next engineer knows it's load-bearing and why, and doesn't "simplify" it back.
- **Guard the win with a benchmark gate.** An optimization with no [regression test](../07-performance-budgets-and-regression-testing/professional.md) is one refactor away from silently reverting — and now you have ugly code that's *also* slow. The gate is what makes the readability cost worth paying.
- **Prefer wins that *lower* complexity.** The best CPU optimizations — better algorithm, less allocation, fewer round-trips — frequently delete code. Reach for those first not only because they're bigger wins but because they have *negative* maintenance cost. Save the readability-eroding micro-optimizations for the proven, isolated, gated hot kernel.

> **The senior-vs-professional distinction:** the senior can make code fast. The professional knows that fast code someone has to maintain for five years has an ongoing cost, and prices that cost into the decision — keeping optimized code rare, contained, documented, and gated, so the speed is permanent and the complexity is quarantined.

---

## Decision Frameworks

**Should I optimize this at all? Ask:**
- What's the annual compute cost of this service, and is CPU its scaling constraint? → if cost is low or CPU isn't binding, stop; the win isn't dollars.
- What fraction of *aggregate* CPU is this code? → Amdahl-cap the realizable win before estimating effort.
- Cost saved per engineer-month vs the engineer-month's cost? → if it's not clearly positive, the time is better spent elsewhere.

**At what altitude? Ask, top-down:**
- Is the algorithm/complexity right? → fix here first; biggest win, often *lowers* complexity.
- Are the data structures right? → next.
- Is the memory layout right (cache, false sharing, allocation)? → next.
- Only now: does a *proven, isolated, gated* micro-arch / native kernel pay? → last resort.

**Free wins before hand-work? Always try:**
- PGO/AutoFDO turned on with a fresh prod profile, re-measured. → fleet-wide %, near-zero maintenance.
- Benchmarked `-O3`/ThinLTO per target. → sometimes free, sometimes negative — measure.

**Flags. Default to:**
- `-O2`, fleet-pinned `-march=x86-64-v3` (never `native`), ThinLTO + PGO for release, ISA verified in CI.

**Drop to a native kernel only when:**
- Measured dominant CPU fraction, higher altitudes exhausted, PGO on, AND you'll add a reference impl + differential tests + a documented "why" + batched FFI.

---

## Common Mistakes

1. **Optimizing without doing the dollar arithmetic.** A 5% win on a cheap service loses money once you price the engineer-month. Multiply `cores × $/core-hour × % × 8760` first; it takes five minutes and reframes the whole project.

2. **Confusing "binding constraint."** A CPU win on a service that scales on memory or a replica floor saves no money — it buys headroom, not cash. Confirm what the autoscaler keys on.

3. **Starting at the bottom altitude.** Hand-vectorizing a loop that an algorithmic fix would delete is wasted effort. Exhaust algorithm → data structure → layout before reaching for intrinsics.

4. **Not turning on PGO.** Leaving a fleet-wide 5–15% on the table while hand-tuning is the most common high-cost omission. PGO/AutoFDO is hours of work for a recurring percentage win.

5. **`-march=native` in a shared build.** It encodes the build machine's incidental ISA as a hard runtime requirement and SIGILLs on older hosts. Pin an explicit fleet baseline; verify the emitted ISA in CI.

6. **Blanket `-O3`.** Often zero or negative (i-cache pressure, code bloat) and surfaces more UB. Benchmark it per target; keep `-O2` as the default.

7. **A native kernel with no reference and no differential tests.** Subtle SIMD/edge-case bugs ship silently. Keep a pure-host reference as the oracle and fuzz-differential it in CI.

8. **Optimized code with no comment and no benchmark gate.** The next engineer "simplifies" it back, or it silently regresses — leaving you with ugly code that's also slow. Document the measurement; gate the win.

---

## Apply it

1. Define the user or business outcome that **CPU-Bound Optimization** should improve.
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

- Which measurable outcome justifies investing in CPU-Bound Optimization?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
- You sped up a micro-benchmark 2x, but the production service got no faster — why?
- Throughput is fine but tail latency (p99) is bad on a CPU-bound service — how do you reason about it?
- What is Profile-Guided Optimization, and when is it worth the build complexity?
- You've optimized a hot path in a managed-language service as far as it'll go — when do you drop to C/Rust, and what's the real cost?
- How do you weigh a 15% speedup against the maintainability cost of the code that achieves it?
- A teammate wants to rewrite a core module in branchless SIMD for performance — how do you evaluate the proposal?
