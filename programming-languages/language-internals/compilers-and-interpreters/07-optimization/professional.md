# Optimization — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Optimization** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The Four-Stage Optimized Build

A maximally-optimized native build is a pipeline, not a flag:

1. **Per-module optimization** (`-O2`/`-O3`): the standard intra-module pass pipeline (`senior.md`) on each translation unit.
2. **Link-time optimization** (ThinLTO): cross-module inlining, whole-program devirtualization, IPCP across the entire binary.
3. **Profile-guided optimization** (PGO): a production/training profile steers inlining, block layout, and branch hints in stages 1–2.
4. **Post-link optimization** (BOLT/Propeller): the *linked* binary is re-laid-out using a profile — hot/cold splitting and basic-block reordering that even LTO can't do because it operates on final addresses.

These compose multiplicatively-ish (each captures wins the others can't): a large C++ service might see ~10–15% from ThinLTO, another ~10–20% from PGO, and a further ~5–10% from BOLT — but only with disciplined profiles and budgets. The professional job is sequencing these stages, feeding each the right profile, and keeping the whole thing reproducible and fast enough to ship.

### 2. ThinLTO at Scale

Full (monolithic) LTO gives the best cross-module scope but serializes the whole program through one optimizer — it doesn't fit large binaries (memory, no parallelism, no incrementality). **ThinLTO** is the scalable answer: each module emits a compact **summary** (call graph, symbol info), a fast "thin-link" phase uses the summaries to decide which functions to *import* into which modules for inlining, and then modules are optimized **in parallel** and **cacheable** per-module. You get ~80–95% of full-LTO's benefit at a fraction of the link time, with incremental rebuilds and distributed caching intact.

The professional concerns: thin-link is a serial bottleneck (watch its scaling); cross-module inlining decisions need profile data to be good (ThinLTO + PGO together is the standard high-end config); and ThinLTO *exposes* whole-program problems (ODR violations, UB hidden by translation-unit boundaries) that per-file builds masked — so adopting it is also a correctness event.

### 3. PGO Profile Pipelines

PGO lives or dies by the **profile**, and the professional problem is the *pipeline that produces and maintains it*.

- **Instrumented PGO** inserts counters, runs a representative training workload, and produces an exact profile. Accurate but requires a separate slow instrumented binary and a curated training corpus.
- **Sampled PGO / AutoFDO / CSSPGO** harvests profiles from *production* via hardware sampling (LBR/`perf`), needing no instrumented build. This is the scalable choice: production *is* the training set, and profiles refresh naturally — but sampling is lossier and needs symbolization infrastructure.

The operational issues that dominate: **freshness** (a profile from an old release applied to new code mislabels hot/cold and can *regress* performance — you need a freshness SLO and automated refresh tied to releases); **representativeness** (a profile from one tenant/region can pessimize others — sometimes you merge multiple profiles); **profile as a build input** (it must be versioned, cached, and reproducible, which complicates hermetic builds); and **the chicken-and-egg of new code** (functions with no profile fall back to static heuristics — you accept a warm-up period). PGO's headline 5–20% is real, but it's an *operational* number that depends on running the pipeline well.

### 4. Post-Link Optimization (BOLT / Propeller)

Even after LTO and PGO, the *final linked binary's* code layout is suboptimal for the i-cache and the branch predictor, because layout decisions were made before final addresses existed. **BOLT** takes the linked binary plus a `perf` profile and *rewrites* it: it reorders basic blocks so hot paths fall through, splits cold code (error handling, slow paths) into separate sections, and reorders functions to cluster hot ones — keeping the instruction cache and TLB dense with code that actually runs. Reported wins on large server binaries are commonly 5–15% on top of PGO, dominated by i-cache and iTLB miss reduction. **Propeller** achieves similar via relinking with basic-block labels, fitting build systems that prefer re-linking over binary rewriting. The trade: another pipeline stage, another profile to manage, and a binary-rewriting (or relink) step in the release path that must be correct and reproducible.

### 5. Fleet-Wide Flag Governance

At scale, optimization flags are **policy** that hundreds of engineers operate under, and the wrong default ships everywhere. The three axes:

- **`-O` level / size:** Default `-O2` for most services; `-Os`/`-Oz` for i-cache-bound or binary-size-constrained targets (often *faster* there); `-O3` only with per-target benchmark justification. The policy should *forbid* casual `-O3` and *require* measurement.
- **Floating-point semantics:** `-ffast-math` must be **off by default fleet-wide** and only enabled in isolated, numerically-tested translation units — it silently changes results (reassociation, NaN folding) and a global default has caused real correctness incidents. Prefer the granular knobs (`-ffp-contract`, `-fno-math-errno`) under explicit ownership.
- **UB hardening:** Decide org-wide which UB to *neutralize* (`-fwrapv`, `-fno-strict-aliasing`, `-fno-delete-null-pointer-checks` for kernel/legacy/security-sensitive code) versus which to *exploit* (default, for max performance) — and pair the aggressive default with mandatory sanitizers in CI so the exploited UB is actually absent.

Governance means: a single source of truth for default flags, a review gate for overrides (especially `-ffast-math` and `-O3`), and documentation of *why* each non-default flag exists so it survives team turnover.

### 6. Correctness Engineering for Optimized Builds

The more aggressive the optimization, the larger the blast radius of any latent bug *or* optimizer bug — so correctness must be engineered, not assumed:

- **Sanitizers in CI as a gate:** UBSan + ASan + TSan runs (at `-O1`/`-O2`) are the precondition for trusting UB exploitation. A clean sanitizer run means the assumptions the optimizer makes about your code actually hold.
- **Differential testing:** build the same code at `-O0` and `-O2`/LTO/PGO and compare outputs on a large input corpus; a divergence is either a miscompile or (far more often) UB. Fuzzing (`libFuzzer`, OSS-Fuzz) feeds this.
- **Translation validation (Alive2):** for teams that touch the compiler or rely on cutting-edge transforms, per-transform equivalence proofs catch optimizer miscompiles that testing misses. Most orgs *consume* a compiler validated this way upstream.
- **Miscompile triage discipline:** when `-O2` "breaks," the runbook is: reproduce under sanitizers (is it our UB?), bisect the `-O` level and the pass (`-print-after-all`, `opt-bisect`), minimize with `creduce`, and only then file upstream. Reflexively dropping to `-O0` hides the bug and forfeits the performance.
- **Reproducibility:** optimized builds must be deterministic given identical inputs *including the profile artifact* — otherwise you can't bisect, can't cache, and can't trust your supply chain.

### 7. The Cost/Benefit Accounting

Every stage costs build time, infrastructure, and correctness surface; the professional decision is *which to run* based on attributable wins. Frame it as: ThinLTO (moderate link cost, broad win, mostly safe) → PGO (profile pipeline cost, large win, freshness risk) → BOLT (extra release stage, i-cache win, binary-rewrite risk). For a latency-sensitive service at fleet scale a 10% CPU win is enormous and justifies all three; for a small internal tool, plain `-O2` is the right stopping point. The discipline is *measuring the win per stage on the real workload* and not paying for complexity that doesn't move the fleet number.

---

## Code Examples

### ThinLTO + PGO, instrumented (Clang)

```bash
# Stage A: build instrumented, run training workload, merge raw profiles.
clang -O2 -fprofile-generate=prof_raw -flto=thin app.c -o app.instr
./app.instr < representative_workload          # produces prof_raw/*.profraw
llvm-profdata merge -output=app.profdata prof_raw/*.profraw

# Stage B: optimized build consuming the profile + ThinLTO.
clang -O2 -fprofile-use=app.profdata -flto=thin \
      -fuse-ld=lld app.c -o app.opt
```

ThinLTO inlines across translation units in parallel; PGO tells the inliner *which* cross-module calls are hot enough to import. The two together are the standard high-end native config.

### Sampled PGO from production (AutoFDO)

```bash
# Collect a profile from the running production binary (no instrumentation):
perf record -b -e cycles:u -o perf.data -- ./app.prod   # -b = LBR for AutoFDO
create_llvm_prof --binary=./app.prod --profile=perf.data --out=app.afdo

# Rebuild using the production-sampled profile:
clang -O2 -fprofile-sample-use=app.afdo -flto=thin app.c -o app.opt
```

Production *is* the training set; profiles refresh with each release. The cost is symbolization and sampling infrastructure, not a slow instrumented binary.

### Post-link optimization with BOLT

```bash
# 1) Build with relocations preserved so BOLT can rewrite layout:
clang -O2 -flto=thin -Wl,--emit-relocs -fuse-ld=lld app.c -o app.opt

# 2) Profile the linked binary in production:
perf record -e cycles:u -j any,u -o perf.data -- ./app.opt
perf2bolt -p perf.data -o app.bolt.fdata app.opt

# 3) Rewrite the binary for hot/cold layout:
llvm-bolt app.opt -o app.bolted -data=app.bolt.fdata \
      -reorder-blocks=ext-tsp -reorder-functions=hfsort -split-functions \
      -split-all-cold -icf=1
```

BOLT reorders basic blocks (hot fall-through), splits cold paths out of hot functions, and clusters hot functions — squeezing i-cache/iTLB wins that survive even after LTO+PGO.

### A flag-governance configuration (Bazel-style policy sketch)

```python
# //build:optimization.bzl  — the single source of truth for default flags.
DEFAULT_COPTS = [
    "-O2",
    "-fno-fast-math",                 # fast-math OFF fleet-wide
    "-fstack-protector-strong",
]
# Overrides require explicit, reviewed opt-in per target:
FASTMATH_COPTS = ["-ffp-contract=fast"]      # granular, not full -ffast-math
HARDENED_UB    = ["-fno-strict-aliasing",    # for legacy/kernel-style targets
                  "-fno-delete-null-pointer-checks"]
# CI builds a parallel sanitizer config as a correctness GATE:
SANITIZER_COPTS = ["-O1", "-fsanitize=address,undefined", "-fno-omit-frame-pointer"]
```

The policy lives in code, overrides are reviewable, and a sanitizer build runs as a gate — so the UB the production build *exploits* is provably absent.

### Differential test harness (pseudo-shell)

```bash
clang -O0            app.c -o app.O0
clang -O2 -flto=thin -fprofile-use=app.profdata app.c -o app.opt
# Replay a large corpus through both; any divergence => miscompile OR our UB.
for input in corpus/*; do
  diff <(./app.O0 < "$input") <(./app.opt < "$input") \
    || echo "DIVERGENCE on $input  (run under UBSan/ASan to classify)"
done
```

A divergence is the alarm; sanitizers classify it (your UB ~99% of the time, an optimizer miscompile rarely). Fuzzing feeds `corpus/`.

---

## Coding Patterns

- **Make the optimized build a versioned pipeline artifact.** Profiles, flag policy, and post-link steps are checked-in, reviewed inputs — not tribal knowledge in a release engineer's shell history.
- **Tie profile freshness to releases.** Automate profile collection from production and refresh on each release; alert when profile age exceeds the freshness SLO.
- **Gate aggressive optimization on a clean sanitizer build.** CI runs ASan/UBSan/TSan; the production build's UB exploitation is only as safe as that gate is green.
- **Default safe, override reviewed.** `-O2` + fast-math-off + UB-hardened-where-needed as the default; `-O3`/`-ffast-math`/UB-exploitation as reviewed, justified, benchmarked overrides.
- **Measure per stage, attribute per stage.** Benchmark the delta from each of LTO, PGO, BOLT on the real workload; drop any stage whose win doesn't justify its cost.

---

## Best Practices

- **Adopt ThinLTO before full LTO, and PGO before BOLT.** Sequence by win-per-complexity; ThinLTO scales and caches, full LTO usually doesn't justify itself on large binaries.
- **Run sampled PGO (AutoFDO) over instrumented where you can.** Production traffic is the best, self-refreshing training set, and it avoids maintaining a slow instrumented binary and a synthetic corpus.
- **Keep `-ffast-math` off fleet-wide; isolate and test any exception.** This is the single most common cause of "the math changed in production." Use granular FP flags under explicit ownership.
- **Make builds reproducible including the profile.** Deterministic outputs are non-negotiable for bisection, caching, and supply-chain integrity.
- **Have a miscompile runbook.** Sanitizers → `-O`/pass bisection (`opt-bisect`, `-print-after-all`) → `creduce` → upstream report. Never resolve a suspected miscompile by silently lowering `-O`.
- **Budget build time as a first-class SLO.** LTO link time and instrumented runs can balloon CI latency; track and cap them, use distributed caching (ThinLTO is cache-friendly).

---

## Edge Cases & Pitfalls

- **Stale PGO/BOLT profile regressing production.** The classic operational failure: profile from an old release labels new hot code as cold and *pessimizes* it. Enforce a freshness SLO and automated refresh.
- **LTO surfacing an ODR/UB bug as a "build break."** Cross-module inlining reveals one-definition-rule violations and UB that per-file builds hid. It's not LTO breaking your code — it's LTO finding the bug. Gate adoption behind differential tests.
- **`-ffast-math` leaking via a build preset or dependency.** A default in a shared toolchain config silently reassociates FP and folds NaN checks across unrelated code. Audit the full flag set; scope fast-math to specific targets.
- **Non-reproducible optimized build defeating bisection.** If the build (or the profile) isn't deterministic, you can't isolate which change caused a regression. Pin everything, including profile artifacts.
- **BOLT/post-link step breaking on the wrong binary format or missing relocations.** PLO needs `--emit-relocs` (or BB labels) and an exact profile-binary match; a mismatch silently no-ops or corrupts layout. Verify the post-link stage in CI.
- **Sanitizer gate too weak to back the UB you exploit.** If CI runs ASan but not UBSan/TSan, the production build still exploits UB the gate doesn't catch. Match the gate's coverage to the UB you rely on being absent.
- **`-O3` shipped fleet-wide "because bigger is better."** Code bloat raises i-cache misses across the fleet — a net regression measured in aggregate even if a microbenchmark improved. Default `-O2`; require evidence for `-O3`.
- **Profile from one region/tenant pessimizing others.** A single-source profile over-fits one workload. Merge representative profiles or run per-class profiles when workloads genuinely diverge.

---

## Apply it

1. Define the user or business outcome that **Optimization** should improve.
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

- Which measurable outcome justifies investing in Optimization?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
