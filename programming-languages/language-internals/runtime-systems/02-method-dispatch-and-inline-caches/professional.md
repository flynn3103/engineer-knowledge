# Method Dispatch & Inline Caches — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Method Dispatch & Inline Caches** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The IC Is the JIT's Type Sensor

The single most important professional reframing: **the inline cache is dual-purpose.** Its first job is dispatch acceleration (skip the lookup). Its second, equally important job is **type profiling**: the set of shapes recorded in a call site's IC during baseline/interpreted execution is exactly the information the optimizing compiler needs. When V8's TurboFan or HotSpot's C2 compiles a hot function, it consults each call site's accumulated IC state and asks: *Is this site monomorphic? Then devirtualize and inline unconditionally (with a deopt guard). Polymorphic with 2–3 types? Polymorphic-inline them. Megamorphic? Leave it as a generic call.* The optimizer's most consequential decisions are driven by IC feedback. This is why warmup matters: a function compiled before its ICs have seen representative types gets bad inlining decisions.

### 2. V8's Tiering Through the Dispatch Lens

V8 runs four tiers, and dispatch/type-feedback threads through all of them:

- **Ignition (interpreter):** executes bytecode; its inline caches collect type feedback into per-site *feedback vectors*. This is where shapes are first observed and recorded.
- **Sparkplug (baseline JIT):** a fast, non-optimizing compile that keeps using the same ICs/feedback vectors — quick code, still collecting feedback.
- **Maglev (mid-tier optimizing JIT):** uses the feedback to do moderate speculative optimization, including devirtualization and some inlining, at lower compile cost than the top tier.
- **TurboFan (top-tier optimizing JIT):** the heavy optimizer; reads the feedback vectors, speculatively devirtualizes monomorphic/polymorphic sites, inlines aggressively, and inserts deopt points guarded by shape checks.

A property access or call that stayed monomorphic through Ignition/Sparkplug becomes, in TurboFan, an inlined load from a fixed offset / an inlined method body behind a single guard. A site that went megamorphic in the lower tiers is compiled to a megamorphic stub call that TurboFan won't inline. The pipeline is, end to end, **a machine for converting stable type feedback into inlined machine code.**

### 3. SpiderMonkey's CacheIR

SpiderMonkey (Firefox) factors ICs through an intermediate representation called **CacheIR**: each IC attaches a small sequence of CacheIR operations describing "guard shape == S, then load slot k" (or "guard klass, call target"). The baseline interpreter and JITs share these CacheIR stubs, and the optimizing tier (WarpMonkey/Ion) consumes the accumulated CacheIR/type information to inline and specialize. The professional point is the same as V8's: **the IC is a structured, compiler-readable description of the site's observed types**, not just an opaque cache — which is what lets a later tier reconstruct exactly what to speculate on.

### 4. HotSpot C2 Inlining Decisions

HotSpot's C2 is the canonical example of dispatch driving inlining in a statically-typed VM:

- **CHA first.** If class hierarchy analysis proves a single implementor of a virtual/interface method, C2 devirtualizes to a direct call and inlines it (subject to the inlining budget), recording a dependency that deoptimizes the method if a conflicting class is later loaded.
- **Profile-guided speculation next.** If CHA can't prove uniqueness, C2 reads the call site's type profile (gathered by C1/the interpreter). A monomorphic profile → guarded inline of the hot type + uncommon trap on miss. A bimorphic/2-type profile → polymorphic inline of two targets + fallback. Megamorphic → a real virtual/interface call, not inlined.
- **The inlining budget gates it all.** Even a devirtualized call is only inlined if the callee fits the budget (`MaxInlineSize`, `FreqInlineSize`, etc.). A large hot method may be devirtualized but not inlined, capturing the call-cost win but not the cross-call optimization win.

`invokeinterface` is handled the same way but starts from a higher base cost (itable resolution), so devirtualizing an interface call is an even bigger relative win.

### 5. The Real Cost (and Value) of `final` / `sealed`

`final` (Java/Kotlin), `sealed` (C#/Kotlin/Scala/Java sealed classes), and non-virtual (C++) are not micro-optimizations to sprinkle blindly — but on hot paths their value is concrete and quantifiable:

- They let the compiler **prove** a unique target instead of speculating, which eliminates the type guard entirely (no compare-and-branch) and removes the deopt dependency (no recompilation risk from class loading).
- A `final` method on a `final` class is the strongest case: the call is provably direct and inlinable with zero runtime checks.
- The win is *not* usually in the call instruction itself (a well-predicted virtual call is cheap); it's in **enabling unconditional inlining** and the optimizations downstream (constant folding of the now-visible body, escape analysis that can stack-allocate or scalar-replace, lock elision).

The honest caveat: modern JITs already devirtualize most effectively-monomorphic calls via CHA/speculation, so `final` often doesn't change steady-state performance much. Its biggest practical value is (1) on truly open-world hot paths where CHA can't help, (2) removing deopt risk in plugin/classloader-heavy systems, and (3) as a correctness/intent declaration. Reach for it deliberately, measure, and don't expect magic on already-monomorphic sites.

### 6. Deoptimization Economics

Speculation has a price tag, and a professional models it:

- **A single deopt** is moderately expensive: it discards the optimized frame, reconstructs the interpreter/baseline state, and the method must be re-profiled and recompiled. A handful of deopts during warmup are normal and healthy.
- **A deopt *storm*** — a site whose guard keeps failing because the type genuinely flips — is pathological. Each flip pays the deopt cost *and* re-optimizes on a now-stale assumption, only to deopt again. The result can be *slower than never optimizing*.
- The runtime defends itself: after enough deopts at a site, it stops speculating there and compiles a stable (polymorphic or megamorphic) version. But the warmup waste already happened.
- **The engineering implication:** a site that is honestly polymorphic should be *allowed* to be polymorphic (let the PIC/polymorphic-inline handle it), not forced into a monomorphic speculation that keeps deopting. Over-speculation is as harmful as no speculation. Diagnosing a deopt storm (via `--trace-deopt` / `-XX:+PrintDeoptimization`) and *relaxing* the hot path's type assumptions is a real, recurring fix.

### 7. Engineering Megamorphic Sites Out of a System

The headline production skill. A megamorphic hot call site is almost always fixable, and the playbook is concrete:

1. **Find it.** Use the runtime's IC tracing (`node --trace-ic`, `--trace-opt`/`--trace-deopt`; `-XX:+PrintInlining`, `-XX:+PrintCompilation`, JFR; SpiderMonkey's IC logging) and CPU profilers measuring indirect-branch mispredicts (`perf stat -e branch-misses`, `perf record` on the hot frame).
2. **Classify it.** Is it *essential* polymorphism (genuinely many types, e.g. a generic serializer) or *accidental* (fragmented shapes, an over-general `Object`/`interface{}` container, conditional field init)?
3. **For accidental polymorphism:** stabilize shapes (consistent construction order, no `delete`, no late field addition), homogenize collections, and tighten static types so the site sees one shape.
4. **For essential polymorphism:** hoist the type discrimination to a single point (a `switch`/type dispatch) and route to type-specialized functions whose internal sites are monomorphic; or shard the hot path by type; or accept a small, healthy PIC (2–4) rather than fighting it.
5. **Verify.** Re-trace and re-profile: the site should now be monomorphic/polymorphic, indirect-branch mispredicts should drop, and the optimizer's inlining log should show the hot callee inlined.

The recurring lesson: **megamorphism is usually a data-shape or API-generality problem, not an inherent property of the algorithm.**

### 8. Cross-Language Synthesis

The professional view unifies the runtimes: V8/SpiderMonkey use ICs to profile shapes in dynamically-typed code and feed an optimizing JIT; HotSpot uses ICs and CHA to profile/prove receiver classes in statically-typed bytecode and feed C2; Go does ahead-of-time itab-based interface dispatch with some compiler devirtualization and no IC tier; C++ does fully static vtable dispatch with optional whole-program/LTO devirtualization. They differ in *when* the type information is available (runtime profile vs compile-time proof) but agree on the goal: **resolve the target uniquely so the body can be inlined and optimized, and keep the hot path's type distribution stable enough that the resolution holds.**

---

## Code Examples

### Reading V8's IC and Deopt Traces

```javascript
// save as dispatch.js, run:  node --trace-ic --trace-opt --trace-deopt dispatch.js
function hot(o) { return o.value(); }

class Stable { value() { return 1; } }
class Other  { value() { return 2; } }

// Phase 1: monomorphic warmup -> IC becomes MONO, TurboFan inlines Stable.value
for (let i = 0; i < 2e6; i++) hot(new Stable());

// Phase 2: introduce a second type AFTER optimization -> guard fails -> DEOPT
for (let i = 0; i < 10; i++) hot(new Other());   // watch --trace-deopt fire here
```

`--trace-ic` shows the `o.value()` site go monomorphic; `--trace-opt` shows `hot` optimized with `Stable.value` inlined; `--trace-deopt` shows the deopt when `Other` arrives. This is the sensor → actuator → safety loop, observable on your laptop.

### Observing HotSpot Inlining and CHA

```java
// Run:  java -XX:+UnlockDiagnosticVMOptions -XX:+PrintInlining \
//            -XX:+PrintCompilation -XX:+PrintDeoptimization Bench
abstract class Op { abstract int apply(int x); }
final class Inc extends Op { int apply(int x) { return x + 1; } }

public class Bench {
    static int run(Op op, int n) {
        int s = 0;
        for (int i = 0; i < n; i++) s = op.apply(s);  // virtual call -> CHA devirtualizes
        return s;
    }
    public static void main(String[] a) {
        Op op = new Inc();
        for (int w = 0; w < 20; w++) run(op, 1_000_000);  // warm up to C2
    }
}
```

`-XX:+PrintInlining` will show `Inc::apply` inlined into `run` (`inline (hot)`), because with only `Inc` loaded, CHA proves a unique target. Add a second `Op` subclass and load it, and you'll see a deopt followed by recompilation to a guarded or virtual form.

### Demonstrating a Deopt Storm (and its fix)

```javascript
// BAD: the site flips type every iteration -> repeated deopt/reoptimize
function bad(items) {
  let s = 0;
  for (const it of items) s += it.weight();   // alternating types here
  return s;
}
// items = [A, B, A, B, ...] where A.weight and B.weight differ
// --trace-deopt shows recurring deopts; throughput is awful.

// FIX: stop forcing monomorphic speculation; sort/group by type so each
// run of the loop is type-stable, OR hoist a single dispatch:
function good(items) {
  let s = 0;
  for (const it of items) {
    s += (it instanceof A) ? aWeight(it) : bWeight(it);  // monomorphic callees
  }
  return s;
}
```

`bad` mis-speculates and deopts on every flip. `good` either keeps callees monomorphic or replaces the unstable virtual call with a stable, predictable branch. Measure both with `--trace-deopt`: the storm disappears.

### Go Compiler Devirtualization (conceptual)

```go
// Go's compiler can devirtualize an interface call when it can prove the
// concrete type at the call site (e.g. the value was just constructed).
func sum(rs []io.Reader) {} // general: indirect calls per element

func process() {
    var r io.Reader = &bytes.Reader{}   // concrete type known here
    _ = r.Read(nil)                     // compiler may devirtualize to (*bytes.Reader).Read
}
```

When the concrete type is statically evident, Go's compiler can turn the interface call into a direct (inlinable) call — the AOT analogue of CHA. When it can't (a slice of arbitrary `io.Reader`), the call stays indirect through the itab. Inspect with `go build -gcflags=-m` for inlining and devirtualization decisions.

### Measuring Indirect-Branch Mispredicts (Linux)

```bash
# Compare a monomorphic vs megamorphic workload at the hardware level.
perf stat -e branches,branch-misses,instructions,cycles ./mono_workload
perf stat -e branches,branch-misses,instructions,cycles ./mega_workload
# Expect the megamorphic run to show a far higher branch-miss rate and lower IPC,
# even if the source 'work' looks identical. Then drill in:
perf record -e branch-misses ./mega_workload && perf report   # find the hot indirect call
```

This is how you confirm, with hardware counters, that a slowdown is dispatch-driven (mispredicted indirect branches and depressed IPC) rather than, say, allocation or cache-capacity misses.

---

## Coding Patterns

### Pattern 1: Warm the right types before measuring

```text
Run a representative warmup that exercises the SAME type distribution as production
before taking measurements (or before relying on steady-state latency). Microbenchmarks
that warm with one type and run with another measure deopt, not steady state.
```

### Pattern 2: Hoist dispatch, specialize callees (interpreter pattern)

Move the polymorphism to one `switch`/type-dispatch and call type-specialized functions; each callee's internal call sites then see one type and inline cleanly. This converts one megamorphic site into N monomorphic ones.

### Pattern 3: Stabilize shapes at the data-construction boundary

Centralize object construction so every instance of a logical type gets the identical shape (same fields, same order, no post-hoc mutation). Treat "shape fragmentation" as a code smell to be fixed at the factory, not at the call site.

### Pattern 4: Let honestly-polymorphic sites be polymorphic

Don't force a 3-type site to mis-speculate as monomorphic (deopt storm). Allow a small PIC / polymorphic inline. Over-speculation is a bug.

### Pattern 5: Use `final`/`sealed`/concrete on proven-hot, proven-stable leaves

After profiling identifies a hot, genuinely non-overridden method, seal it to remove guards and deopt dependencies — especially valuable in classloader-heavy systems.

---

## Best Practices

- **Diagnose with the runtime's own tools first.** IC traces, inlining logs, and deopt logs tell you exactly what the optimizer did and why — far more reliable than guessing from source.
- **Separate "didn't devirtualize" from "didn't inline."** The first is a type-stability problem; the second is a code-size/budget problem. They have different fixes.
- **Treat deopt storms as P1 perf bugs.** Recurring deopts can make optimized code slower than the interpreter. Find them with `--trace-deopt`/`PrintDeoptimization` and relax the offending speculation.
- **Always reason in steady state for production latency.** Discard warmup-window measurements; ensure benchmarks reach a converged tier/IC state.
- **Fix megamorphism at the data/API layer, not with micro-tweaks.** Homogenize shapes and collections, or restructure dispatch — don't paper over it.
- **Measure `final`/`sealed` impact; don't cargo-cult it.** It's a real lever in specific situations (open-world hot paths, deopt-prone systems), not a universal speedup.
- **Respect warmup in deployment.** For latency-critical JVM/Node services, account for cold-start/warmup (pre-warming, AOT/CDS, or accepting a ramp) so users don't hit un-optimized dispatch.

---

## Edge Cases & Pitfalls

- **A microbenchmark that "proves" `final` is free** likely tested an already-monomorphic site CHA had handled anyway. Test the open-world / multi-implementor case to see the real effect.
- **Production sees megamorphic where the test saw monomorphic** because production data has more type variety. The benchmark's type distribution must match production's, or the IC states diverge and the numbers are meaningless.
- **Classloader/plugin loading triggers mid-run deopts.** A hot path optimized via CHA can deoptimize when a plugin loads a new subtype — a latency spike unrelated to the request itself. Pre-load or seal to avoid.
- **OSR-compiled loops can have different inlining than method-entry compiles.** A long-running loop entered via OSR may inline differently than the same code reached normally; don't assume one trace generalizes.
- **GC and shape transitions interact.** In some engines, certain object operations (property deletion, very large objects) move objects to dictionary mode, permanently degrading their ICs even after the operation; the slowdown outlives the cause.
- **`instanceof`/type-switch hot paths can themselves go megamorphic.** Replacing virtual dispatch with a manual type ladder doesn't help if the ladder is long and the type distribution is flat — you've just moved the unpredictable branch.
- **Speculation can hide correctness-relevant type assumptions.** A guard that "never fails in testing" but can fail in production turns into a deopt under rare inputs — a performance failure mode that only manifests at scale.

---

## Apply it

1. Define the user or business outcome that **Method Dispatch & Inline Caches** should improve.
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

- Which measurable outcome justifies investing in Method Dispatch & Inline Caches?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
