# Deoptimization & Speculation — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Deoptimization & Speculation** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The cross-engine model (same idea, four dialects)

All speculative JITs share the bet/guard/deopt core, but differ in vocabulary, tiers, and how aggressively they deopt:

```text
ENGINE         TIERS (roughly)                   "DEOPT" CALLED      NOTES
V8 (JS)        Ignition -> Sparkplug -> Maglev    "deopt"/"bailout"   FeedbackVector-driven;
               -> TurboFan                                            shapes(maps)+elements kinds.
HotSpot (JVM)  Interpreter -> C1 -> C2            "uncommon trap" /   CHA + profiling; lazy
               (Graal as alt C2)                  "not entrant"       invalidation on class load.
SpiderMonkey   Interpreter -> Baseline ->         "bailout"           Bails between IonMonkey/
               WarpMonkey/Ion                                         Warp and Baseline.
.NET CLR       Interpreter? no -> QuickJIT(T0)    NOT speculative-    Tiers UP via call counts;
               -> Tier-1(opt, Dyn-PGO)            deopt in the        does not abandon a frame
                                                  V8/HotSpot sense    mid-run on a broken type bet.
```

The .NET distinction is important and often misunderstood: the CLR's tiering promotes hot methods to an optimized JIT and uses **Dynamic PGO**, but it does **not** speculatively compile a method assuming a type/shape and then *deoptimize a running frame* when the bet breaks the way V8 and HotSpot do. Its guarded devirtualization falls back via a *runtime branch* in the compiled code, not a frame-rewinding deopt. So "deopt storms" as a pathology are primarily a V8 / HotSpot / SpiderMonkey concern; on .NET you reason about tiering, guarded devirt, and PGO quality instead.

### 2. The deopt-reason taxonomy is your primary signal

Every deopt carries a *reason*, and the reason **names the broken bet**. Reading it is the fastest path to root cause:

**V8 (selected):**

```text
wrong map / wrong map dynamic   -> object shape (hidden class) changed
unstable map                    -> shape isn't stabilizing; access keeps changing maps
not a Smi / lost precision       -> integer bet broke (overflow / became double)
not a heap number               -> expected a number, saw something else
hole                            -> array hole encountered where packed assumed
insufficient type feedback      -> site never gathered enough feedback to specialize
out of bounds                   -> index/range speculation broke
```

**HotSpot uncommon-trap reasons (selected):**

```text
class_check / class_check2      -> receiver type not the speculated one (devirt bet broke)
null_check                      -> a non-null speculation hit null
range_check                     -> array bounds speculation broke
unstable_if / unstable_fused_if -> a pruned/biased branch was taken
bimorphic / unloaded            -> call site polymorphism / unloaded class
made not entrant                -> code invalidated (often CHA / class load)
```

Pattern: **a stable reason on a stable site = a real, fixable speculation break.** A scatter of different reasons during the first seconds = normal warm-up.

### 3. Anatomy of a deopt storm and how to kill it

A storm has a signature: the **same function**, the **same reason**, **repeating** long after warm-up, with re-optimization in between. Diagnosis loop:

1. **Confirm it's steady-state, not warm-up.** Let the process run; does the deopt keep firing after minutes / millions of iterations?
2. **Get the reason + site.** `--trace-deopt` (V8) or `PrintCompilation`+`TraceDeoptimization` (HotSpot). The reason names the bet; the position names the site.
3. **Find the input that breaks the bet.** `wrong map` → which call path constructs a different shape? `not a Smi` → which path produces a double/overflow? `class_check` → which subclass got introduced?
4. **Stabilize the speculation at the source** — *not* by disabling optimization:
   - shape break → unify construction so one hidden class is produced;
   - SMI break → keep the loop's value domain integer (or move to typed arrays / accept doubles uniformly);
   - megamorphic → split the site by kind into monomorphic sites;
   - CHA break → make the hot method `final` / avoid late class loading on the hot path.
5. **Verify the storm is gone** (deopt count drops to ~warm-up only) and **lock it with a regression test**.

The anti-pattern fix is reaching for `--no-opt`, `-Xint`, or `-XX:-TieredCompilation` to "stop the deopts." That removes the *symptom* by removing the *fast path* — you end up uniformly slow. Fix the *bet*, not the optimizer.

### 4. Warm-up and tier policy as a production concern

Speculation means **your service is slowest right after it starts** and gets faster as it tiers up. This has real operational consequences:

- **Cold-start latency** (serverless, autoscaling, blue/green deploys) is dominated by un-tiered code. A pod that just came up serves interpreter/baseline-speed traffic.
- **Load-balancer warm-up / slow-start** matters: routing full traffic to a freshly-started JVM/Node process hits its un-optimized phase.
- **Benchmarks must run past warm-up**, or you're measuring the wrong tier. Always discard warm-up iterations; report steady state.
- **Tier flags are policy levers** (use sparingly, measure always): `-XX:TieredStopAtLevel`, `-XX:CompileThreshold`, V8 `--max-opt`, `--no-flush-bytecode`; .NET `DOTNET_TieredCompilation`, `DOTNET_TC_QuickJitForLoops`, `DOTNET_TieredPGO`, ReadyToRun for faster startup.

### 5. Guarded devirtualization vs speculative-deopt devirtualization

A subtle cross-engine point. Both HotSpot and .NET want to turn virtual calls into direct/inlinable ones using profile data. The difference:

- **HotSpot** may *speculatively* devirtualize under CHA and **deopt** (uncommon trap) if a new override appears — frame-rewinding fallback.
- **.NET (Dynamic PGO)** emits **guarded devirtualization**: `if (type == ProfiledType) { inlined fast path } else { normal virtual call }`. The fallback is a *branch in the same compiled method*, not a deopt of the frame.

Both are speculative; only one *deoptimizes*. When tuning .NET, you reason about whether PGO captured the right dominant type (so the guard usually hits), not about deopt storms.

### 6. Telemetry: making invisible deopts observable in production

You rarely run production with `--trace-deopt` (it's noisy/expensive). Instead:

- **JVM:** JFR (Java Flight Recorder) events for compilation and deopt; `jcmd Compiler.*`; async-profiler in *wall/CPU* mode shows time in interpreter vs compiled; `-XX:+PrintCompilation` in canary, not fleet-wide.
- **V8/Node:** `--prof` + tick processor (shows time in optimized vs unoptimized), `--log-deopt` in canaries, `perf` + `--perf-prof` for flame graphs that label optimized vs builtin/interpreter frames; `%GetOptimizationStatus` (with `--allow-natives-syntax`) in tests.
- **SpiderMonkey:** `IONFLAGS`, `--ion-offthread-compile`, JIT spew in dev builds.
- **.NET:** EventPipe / `dotnet-trace` with the JIT provider, `DOTNET_JitDisasmSummary`, ETW compilation events; `dotnet-counters` for time-in-JIT.

The professional move is **canary tracing**: enable verbose deopt logging on one instance, capture, analyze, disable — never fleet-wide.

---

## Code Examples

### Example 1: Query a function's optimization status programmatically (V8)

```js
// status.js  —  run with: node --allow-natives-syntax status.js
function work(o) { return o.x + o.y; }

const a = { x: 1, y: 2 };
for (let i = 0; i < 200000; i++) work(a);     // warm up

%OptimizeFunctionOnNextCall(work);
work(a);
console.log('status:', %GetOptimizationStatus(work));  // bitmask: optimized?

// Break the shape and re-check.
work({ y: 1, x: 2, z: 3 });                    // different map
console.log('after shape change:', %GetOptimizationStatus(work));
```

`%GetOptimizationStatus` returns a bitmask you decode (is-optimized, is-turbofanned, is-interpreted, marked-for-deopt…). This is the canonical way to *assert* optimization state in tests so a regression that causes deopt fails CI.

### Example 2: A deopt-count regression guard (Node, conceptual harness)

```js
// guard.test.js (pseudo) — parse --trace-deopt output and assert a ceiling.
const { execSync } = require('child_process');
const out = execSync('node --trace-deopt ./hot-path-bench.js 2>&1').toString();
const deopts = (out.match(/deoptimizing \(DEOPT/g) || []).length;

// Allow a small warm-up budget; fail if a refactor reintroduces a storm.
if (deopts > 25) {
  throw new Error(`Deopt regression: ${deopts} deopts (budget 25). Check shapes/types.`);
}
console.log(`OK: ${deopts} deopts`);
```

The point isn't the exact threshold; it's making deopt count a **measured, asserted** quantity so storms can't silently creep back in.

### Example 3: JVM — confirm a class-load-driven invalidation wave

```bash
# Run with compilation + deopt tracing; correlate "made not entrant" bursts
# with class-loading on the timeline.
java -XX:+UnlockDiagnosticVMOptions \
     -XX:+PrintCompilation -XX:+TraceDeoptimization \
     -Xlog:class+load=info \
     -jar service.jar | tee jit.log

# Then: grep for invalidation bursts and the class loads just before them.
grep -E "not entrant|made zombie" jit.log     # invalidations
grep "class,load" jit.log                       # what loaded around them
```

If invalidation bursts cluster right after batches of `class,load` lines (e.g. lazy framework init, plugin loading, proxy generation), you've found a CHA-invalidation wave. The fix is to *front-load* class loading (warm up the classpath before serving traffic) so invalidation happens once, during warm-up, not under live load.

### Example 4: .NET — observe tiering / PGO instead of deopt

```bash
# Dynamic PGO on; observe tier transitions and disassembly summary.
DOTNET_TieredPGO=1 \
DOTNET_TieredCompilation=1 \
DOTNET_JitDisasmSummary=1 \
dotnet run -c Release

# Trace JIT activity without verbose flags in prod-like runs:
dotnet-trace collect --providers Microsoft-Windows-DotNETRuntime:0x1000:5 -- dotnet myapp.dll
```

Here you're checking that hot methods reached **Tier-1** and that guarded devirtualization picked the right dominant type — *not* hunting frame-rewinding deopts, which the CLR doesn't do in that sense.

### Example 5: Localizing a megamorphic site that lost inlining (V8)

```js
// Run a CPU profile; in the flame graph the hot site shows time in a generic
// "LoadIC"/"CallIC" builtin rather than inlined into the caller -> megamorphic.
node --prof megabench.js
node --prof-process isolate-*.log > processed.txt
// Look for the site spending time in *IC builtins instead of optimized code.
```

Time concentrated in `*IC` builtins (rather than inlined optimized frames) is the fingerprint of a site that went polymorphic/megamorphic and can no longer be inlined or specialized.

---

## Coding Patterns

### Pattern 1: Front-load class loading / warm-up before serving traffic

```java
// ✅ Warm the JIT and pre-load classes during readiness, not under live load,
//    so CHA invalidations and tier-up happen once, off the hot path.
void warmUp() {
    for (int i = 0; i < 50_000; i++) handle(syntheticRequest());
}
// Gate readiness/health-check on warm-up completion before the LB routes to you.
```

### Pattern 2: Keep DTO/object shapes uniform across construction sites

```js
// ✅ A single factory yields one hidden class everywhere -> shape-stable consumers.
function makeUser(id, name, email) {
  return { id, name, email };          // always same keys, same order
}
// ❌ Constructing the "same" object with different key orders or optional keys
//    in different code paths spawns multiple maps and pushes consumers poly/mega.
```

### Pattern 3: Type-stable hot numeric loops via typed arrays

```js
// ✅ Fixed representation; no SMI/double churn, no elements-kind transitions.
function dot(a /* Float64Array */, b /* Float64Array */) {
  let s = 0;
  for (let i = 0; i < a.length; i++) s += a[i] * b[i];
  return s;
}
```

### Pattern 4: Split a hot megamorphic dispatch into specialized sites

```js
// ✅ One monomorphic site per kind keeps each inlinable.
const handlers = { a: handleA, b: handleB, c: handleC };
function dispatch(msg) {
  const h = handlers[msg.kind];   // table lookup, then...
  return h(msg);                  // ...each handler sees one concrete shape
}
```

### Pattern 5: Make intentionally-final hot virtuals `final` (JVM)

```java
public final class RouteKey { /* hot, hashed; final removes CHA risk */ }
```

---

## Best Practices

- **Read the reason code first.** It names the broken bet; let it drive the investigation instead of guessing.
- **Fix the bet, never disable the optimizer in production.** Door B (stabilize), not Door A (`-Xint`/`--no-opt`).
- **Measure steady state for services, warm-up for cold-start workloads.** Identify the regime before tuning.
- **Canary your tracing.** Verbose deopt/compile logs on one instance, analyze, disable. Never fleet-wide.
- **Gate readiness on warm-up.** Don't let load balancers send peak traffic to un-tiered processes.
- **Assert optimization state in CI.** `%GetOptimizationStatus` / deopt-count budgets / JFR thresholds turn invisible regressions into red builds.
- **Re-verify engine specifics per release.** Tier names, reason strings, and flags change; treat memorized details as perishable.
- **Know .NET is different.** Reason about tiering, guarded devirt, and PGO, not frame-rewinding deopt storms.

---

## Edge Cases & Pitfalls

### Pitfall 1: "I disabled the JIT and it got slower" — yes, that's expected

Turning off optimization to "stop deopts" removes the fast path entirely. It's a *diagnostic* (does the regression involve the optimizer?), never a fix. Steady-state throughput will drop.

### Pitfall 2: Benchmarking inside warm-up

Microbenchmarks that don't discard warm-up iterations measure interpreter/baseline tiers and lie about steady-state performance. Use a proper harness (JMH on JVM; BenchmarkDotNet on .NET; `tinybench`/manual warm-up on Node) that separates warm-up from measurement.

### Pitfall 3: A profiler/debugger triggering deopt-all

Profiling under a debugger, or with certain instrumentation, forces mass deoptimization so the runtime can present interpreter-level state. Your "profiled" numbers then reflect de-optimized code. Use low-overhead sampling profilers (async-profiler, `perf`, EventPipe) that don't deopt.

### Pitfall 4: Framework-induced megamorphism

ORMs, DI containers, proxies, serializers, and bytecode generators inject extra shapes/types into call sites you believed were monomorphic. The regression appears far from the framework code. Profile the *actual* shapes flowing through the hot site, not the source.

### Pitfall 5: Class-load invalidation under live traffic

Lazy class loading, plugin systems, dynamic proxy generation, and reflective bootstrapping can fire CHA invalidations *during* peak traffic, causing throughput dips. Front-load loading during warm-up.

### Pitfall 6: Treating all engines as V8

Porting a "avoid deopt storms" mental model directly to .NET leads to chasing a pathology that mostly doesn't exist there. Match the model to the engine: deopt-driven (V8/HotSpot/SpiderMonkey) vs branch-guarded (.NET).

### Pitfall 7: Over-tuning cold code

Shape-stabilizing and monomorphizing everything makes a codebase rigid and uglier for zero gain on cold paths. Apply JIT-friendly patterns only where a profiler proves heat and a trace proves instability.

### Pitfall 8: Reason-string drift breaking your log parsers

Deopt/uncommon-trap reason strings are *not* a stable API. A regression-guard parser keyed on exact strings can silently break on an engine upgrade. Parse loosely and re-validate after runtime upgrades.

---

## Apply it

1. Define the user or business outcome that **Deoptimization & Speculation** should improve.
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

- Which measurable outcome justifies investing in Deoptimization & Speculation?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
